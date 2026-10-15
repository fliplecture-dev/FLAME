"""F13 transient source generation. Never put executable source in message storage."""
from collections import OrderedDict
from concurrent.futures import Future
from dataclasses import dataclass
import json
import logging
import re
from threading import Lock, Thread
from time import monotonic

from app.modules.teaching.gateway import GatewayError, OpenAIResponsesGateway
from app.modules.teaching.output_guard import has_forbidden_authority_claim
from app.modules.teaching.languages import language_instruction

ENGINES = {"matter", "three", "r3f", "phaser", "rive", "html5"}


def select_engine(question: str) -> str | None:
    """Conservative opt-in routing; normal explanation/math requests remain unchanged."""
    q = question.casefold()
    if re.search(r"\b(?:text.only|no (?:animation|simulation|visual))\b", q):
        return None
    explicit = ((r"\bmatter(?:\.js)?\b", "matter"), (r"\b(?:r3f|react three fiber)\b", "r3f"),
                (r"\bthree(?:\.js)?\b", "three"), (r"\bphaser\b", "phaser"),
                (r"\brive\b", "rive"), (r"\b(?:html5|canvas|svg)\b", "html5"))
    interactive = re.search(r"\b(?:simulat\w*|interactive|animat\w*|dragg\w*|rotat\w*|game)\b", q)
    # An explicit engine plus a visual creation request is already an opt-in.
    # Do not require learners to know the additional word "interactive".
    create_visual = re.search(r"\b(?:creat\w*|show|render\w*|build\w*|draw\w*|display\w*|make|demonstrat\w*)\b", q)
    for pattern, engine in explicit:
        if re.search(pattern, q) and (interactive or create_visual):
            return engine
    if not interactive:
        return None
    if re.search(r"\b(?:3d|solar system|planet|molecule)\b", q):
        return "r3f"
    if re.search(r"\b(?:game|quiz game|platformer)\b", q):
        return "phaser"
    if re.search(r"\b(?:gravity|falling|collision|collid\w*|friction|physics|pendulum|ball|block)\b", q):
        return "matter"
    if re.search(r"\b(?:fractions?|counting|number line|coordinates?|functions?|geometry|triangles?|shapes?|graphs?)\b", q):
        return None  # Existing trusted F12 mathematics remains the default for these goals.
    return "html5" if re.search(r"\b(?:animat\w*|illustrat\w*)\b", q) else None


INSTRUCTION = """Return ONLY JSON {"version":1,"title":"...","description":"...","source":"..."}.
Keep visuals and labels suitable for learners under 15. Do not claim verified sources or official grading.
Generate compact educational JS/JSX: export default function mount(api) returns optional
update(dt), control(name,value), pointer({type,x,y,dx,dy,down}), dispose(). dt is seconds.
Source runs in a disposable worker, no DOM/network/storage/eval/timers/workers/dynamic imports.
api.canvas is OffscreenCanvas 800x450; api.report({numeric measurements}) provides readouts.
The runtime handles pause/resume/reset, pointer events and cleanup. Keep source below 650 tokens.
"""
ENGINE_INSTRUCTIONS = {
    "matter": """Import Matter from 'matter-js'. const engine=api.matterWorld() creates an engine
with floor top y=420 and side walls. Add your own Matter.Bodies/Composite/Body/Events.
The runtime already steps/draws this world, implements mouse/touch dragging, gravity/friction
sliders and disposal. Do NOT create another Engine/Runner/Render or step/draw it yourself.
Return update(){api.report({x:body.position.x,y:body.position.y,...})} as needed.
Friction slider updates all surfaces. Bodies for sliding comparisons use frictionAir:0.
""",
    "r3f": """Import React from 'react', {useFrame} from '@react-three/fiber'. Define JSX meshes/lights,
then await api.render(<Scene/>) in async mount. Camera/orbit, 800x450 root, rendering and
cleanup are provided. Orbit radius<=5. api.orbit reflects pointer orbit. No textures/assets.
""",
    "three": """Import * as THREE from 'three'. const renderer=api.threeRenderer() provides the bounded WebGL renderer; create scene/camera,
800x450 size. Render in update, rotate view from pointer deltas; dispose GPU resources.
""",
    "phaser": """No imports. api.phaser({gravity:1,bodies:[{x:200,y:70,radius:25,color:0x6688ff,
restitution:0.8,friction:0.1,static:false}]}) starts a trusted Phaser Matter scene.
Up to 50 bodies, rectangles use width/height instead of radius. No executable scene code.
Trusted runtime handles dragging, gravity/friction, pause/resume/reset.
""",
    "rive": """No imports. Only existing FLAME-authored Weather World artwork is available.
api.rive({weather:0,wind:0}) controls authored inputs: weather integer0..4 sunny/cloudy/rainy/
windy/snowy; wind0..1. No new .riv creation. Pointer position can adjust wind.
""",
    "html5": "No imports. Animate procedural shapes with api.canvas.getContext('2d') in update(dt). SVG path illustrations can use new Path2D(pathData) and context.fill/stroke; no DOM SVG or external assets.",
}


def generate(gateway, engine: str, question: str, *, response_language: str | None = None) -> dict:
    # Source jobs run independently of HTTP/text streaming. Keep the same model
    # and token cap, but allow code generation one longer attempt, never two bills.
    if isinstance(gateway, OpenAIResponsesGateway):
        gateway = OpenAIResponsesGateway(gateway.key, gateway.model,
                                        timeout_seconds=60, attempts=1,
                                        reasoning_effort="low" if gateway.model.startswith(("gpt-5", "gpt-6", "o3", "o4")) else None,
                                        max_output_tokens=gateway.max_output_tokens)
    result = gateway.generate([{"role": "system", "content": INSTRUCTION + ENGINE_INSTRUCTIONS[engine] + language_instruction(response_language)},
                               {"role": "user", "content": f"Selected engine: {engine}\nLearning request: {question}"}])
    try:
        data = json.loads(result.text)
        if not isinstance(data, dict) or set(data) != {"version", "title", "description", "source"} or type(data["version"]) is not int or data["version"] != 1:
            raise ValueError()
        for field, maximum in (("title", 160), ("description", 500), ("source", 16000)):
            if not isinstance(data[field], str) or not data[field].strip() or len(data[field]) > maximum:
                raise ValueError()
        if has_forbidden_authority_claim(data["title"] + " " + data["description"]):
            raise ValueError()
        return {**data, "engine": engine}
    except (ValueError, TypeError, RecursionError):
        raise GatewayError("invalid_simulation_output") from None


@dataclass
class Entry:
    expires: float
    future: Future


class TransientSimulations:
    """Bounded process-memory dedup; expiry/restart NEVER causes automatic regeneration."""
    def __init__(self, maximum=128, ttl=900, require_arm=False):
        self.entries = OrderedDict()
        self.lock = Lock()
        self.maximum, self.ttl = maximum, ttl
        self.usage = {}
        self.require_arm = require_arm
        self.armed = {}
        self.output_languages = OrderedDict()

    def arm(self, owner, message, *, response_language=None):
        """Only fresh answer finalization grants one short-lived generation opportunity."""
        with self.lock:
            now = monotonic()
            self.armed = {key: expires for key, expires in self.armed.items() if expires > now}
            if len(self.armed) < self.maximum:
                key = (str(owner), str(message))
                self.armed[key] = now + 120
                self.output_languages[key] = (now + self.ttl, response_language)
                while len(self.output_languages) > self.maximum:
                    self.output_languages.popitem(last=False)

    def response_language(self, owner, message):
        with self.lock:
            expires, code = self.output_languages.get((str(owner), str(message)), (0, None))
            return code if expires > monotonic() else None

    def run(self, owner, message, factory, *, start=False, limit=20, background=False):
        key = (str(owner), str(message))
        with self.lock:
            now = monotonic()
            for old in list(self.entries):
                if self.entries[old].expires < now and self.entries[old].future.done():
                    del self.entries[old]
            entry = self.entries.get(key)
            created = entry is None
            if created:
                if not start:
                    return {"status": "expired"}
                if background and sum(not item.future.done() for item in self.entries.values()) >= 4:
                    return {"status": "limited"}
                if self.require_arm and self.armed.pop(key, 0) < now:
                    return {"status": "expired"}
                self.usage = {owner: data for owner, data in self.usage.items() if data[0] > now}
                expires, count = self.usage.get(key[0], (now + 86400, 0))
                if len(self.entries) >= self.maximum or count >= limit or len(self.usage) >= 1024 and key[0] not in self.usage:
                    return {"status": "limited"}
                self.usage[key[0]] = (expires, count + 1)
                entry = Entry(now + self.ttl, Future())
                self.entries[key] = entry
        def complete():
            try:
                entry.future.set_result({"status": "ready", **factory()})
            except Exception as error:
                # Cache failures as well: retries cannot silently bill another provider call.
                safe_codes = {"provider_unavailable", "provider_rate_limited", "provider_budget_exceeded",
                              "invalid_provider_output", "invalid_simulation_output", "provider_output_limit"}
                code = error.code if isinstance(error, GatewayError) and error.code in safe_codes else "simulation_generation_failed"
                logging.getLogger(__name__).warning("simulation_generation_failed: %s", code)
                entry.future.set_result({"status": "error", "code": code})
        if created:
            if background:
                try:
                    Thread(target=complete, daemon=True, name="flame-simulation").start()
                except RuntimeError:
                    entry.future.set_result({"status": "error", "code": "simulation_generation_failed"})
            else:
                complete()
        if background and not entry.future.done():
            return {"status": "pending"}
        try:
            return entry.future.result(timeout=40)
        except TimeoutError:
            return {"status": "pending"}


transient = TransientSimulations(require_arm=True)

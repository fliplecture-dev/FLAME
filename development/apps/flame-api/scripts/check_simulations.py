"""Explicit synthetic live demo source, memory only. No student/database writes."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from app.core.config import Settings
from app.modules.teaching.gateway import OpenAIResponsesGateway
from app.modules.teaching.simulations import generate

questions = [
    ("falling", "matter", "Falling ball with adjustable gravity. Start at x=400,y=60, zero velocity, radius 22, floor at y=430. Use api.matterWorld(); runtime supplies gravity/friction and dragging. Report {x:ball.position.x,y:ball.position.y} every update via api.report. Dragging is supplied by the runtime."),
    ("collision", "matter", "Two draggable balls colliding horizontally. Start touching floor at x=200 and x=480, same y=395, radius30. First ball has horizontal velocity 6, second -3. restitution .9 and friction0, frictionAir0. Count collisionStart events. Report {x:balls[0].position.x,y:balls[0].position.y,collisions:count}. Use api.matterWorld(); dragging and controls are supplied."),
    ("friction", "matter", "Sliding block with adjustable friction. Start block width60 height40 at x=120,y=399, floor top420. Initial velocity x=12, y=0, frictionAir=0. Use api.matterWorld(); its floor and sliders are provided. Initial block friction=.1. Report {x:block.position.x,y:block.position.y}. Do not draw or step physics; runtime handles both."),
    ("solar", "r3f", "Rotatable 3D solar system, illustrative scales. Use compact React JSX: sun radius1.2 and four differently colored planets in a row at x=-4,-2,2,4; small radii. Use meshBasicMaterial so no lights needed. await api.render(element); return {}. Runtime supplies pointer orbit, pause, reset and disposal. No useFrame needed. No textures/assets. Source below 300 tokens."),
]

def main():
    settings = Settings()
    if not settings.llm_openai_api_key:
        raise SystemExit("Configured provider is unavailable")
    gateway = OpenAIResponsesGateway(settings.llm_openai_api_key.get_secret_value(), settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds, max_output_tokens=settings.llm_max_output_tokens)
    specs = {}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            nonlocal specs
            if self.path != "/fixtures":
                self.send_error(404)
                return
            if len(specs) < len(questions):
                for name, engine, question in questions:
                    if name in specs:
                        continue
                    try:
                        spec = generate(gateway, engine, question)
                        specs[name] = {"name": name, **spec}
                        print(f"Generated {name}: engine={engine}, source_characters={len(spec['source'])}", flush=True)
                    except Exception as exc:
                        print(f"Generation failed: {name}; code={getattr(exc, 'code', type(exc).__name__)}", flush=True)
                        continue
            payload = json.dumps(list(specs.values())).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
    print("Synthetic demo source server ready on 127.0.0.1:3138; source stays in memory", flush=True)
    HTTPServer(("127.0.0.1", 3138), Handler).serve_forever()

if __name__ == "__main__":
    main()

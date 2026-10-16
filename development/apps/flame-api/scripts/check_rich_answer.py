"""One synthetic F11/F12 provider smoke. Opt-in, no database or student data."""
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.modules.application.teaching.answer_service import _answer
from app.modules.application.teaching.gateway import GatewayError, OpenAIResponsesGateway
from app.modules.application.teaching.prompt import assemble_open_curiosity
from app.modules.application.teaching.math_visuals import TEMPLATES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Make one paid synthetic call within configured limits")
    parser.add_argument("--math-template", choices=["fraction_bar", "triangle_angles", "linear_function"])
    args = parser.parse_args()
    if not args.execute:
        parser.error("Pass --execute to authorize one synthetic provider call")
    settings = Settings()
    if not settings.llm_openai_api_key or not settings.llm_model:
        parser.error("Configure the existing provider settings first")
    questions={"fraction_bar":"Explain 3/4 with an interactive fraction bar.",
               "triangle_angles":"Let me drag triangle vertices and explore their angles.",
               "linear_function":"Explore how slope changes a linear function with a movable point."}
    question=questions.get(args.math_template,
        "Explain distance at a constant speed of 2 metres per second. Use a short Markdown "
        "explanation with an inline math equation, a two-line Python example in a code fence, "
        "and an illustrative line chart for 1, 2 and 3 seconds. Use the rich JSON answer format.")
    prompt = assemble_open_curiosity(question, [])
    gateway = OpenAIResponsesGateway(settings.llm_openai_api_key.get_secret_value(), settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds, max_output_tokens=settings.llm_max_output_tokens)
    started = perf_counter()
    try:
        generated = gateway.generate(prompt.messages)
        result = _answer(uuid4(), None, generated, max_words=100, rendering_decision=prompt.rendering_decision)
        kinds = [block["kind"] for block in result["blocks"]]
        templates=[block["template"] for block in result["blocks"] if block["kind"]=="math_visual"]
        passed = "markdown" in kinds and (args.math_template in templates if args.math_template else "chart" in kinds)
        print(json.dumps(dict(status="passed" if passed else "missing_requested_blocks", kinds=kinds,
            templates=templates, engines=[TEMPLATES[name]["engine"] for name in templates],
            input_tokens=generated.input_tokens, output_tokens=generated.output_tokens,
            elapsed_ms=round((perf_counter() - started) * 1000), prompt_version=prompt.version)))
        return 0 if passed else 1
    except GatewayError as error:
        print(json.dumps(dict(status="unavailable", code=error.code,
            elapsed_ms=round((perf_counter() - started) * 1000))))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Opt-in live provider deadline probe; no production setting or database change."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import httpx

from app.core.config import Settings
from app.modules.application.teaching.gateway import GatewayError, OpenAIResponsesGateway


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Allow up to two synthetic provider attempts')
    args = parser.parse_args()
    if not args.execute:
        print('No provider calls made. Use --execute for the live timeout probe.')
        return
    settings = Settings()
    if not settings.llm_openai_api_key or not settings.llm_model:
        raise SystemExit('Provider is not configured.')
    gateway = OpenAIResponsesGateway(settings.llm_openai_api_key.get_secret_value(), settings.llm_model,
                                    timeout_seconds=0.001, max_output_tokens=64)
    started = perf_counter()
    timeouts = []
    class ObservedClient(httpx.Client):
        def post(self, *args, **kwargs):
            try:
                return super().post(*args, **kwargs)
            except httpx.TimeoutException as error:
                timeouts.append(type(error).__name__)
                raise
    try:
        with patch('app.modules.application.teaching.gateway.httpx.Client', ObservedClient):
            gateway.generate([{'role': 'user', 'content': 'Say hello.'}])
    except GatewayError as error:
        result = {'date': datetime.now(timezone.utc).isoformat(), 'code': error.code,
                  'elapsed_seconds': round(perf_counter() - started, 3),
                  'timeout_seconds': 0.001, 'maximum_attempts': 2,
                  'observed_timeouts': timeouts,
                  'scope': 'Live provider transport deadline; no DB writes or production settings changed.'}
        if error.code != 'provider_unavailable' or len(timeouts) != 2:
            raise SystemExit('Unexpected provider outcome: ' + error.code)
        destination = Path(__file__).resolve().parents[4] / 'work' / 'b7-live-timeout.json'
        destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result))
        return
    raise SystemExit('Provider answered before the deadline; timeout acceptance was not demonstrated.')


if __name__ == '__main__':
    main()

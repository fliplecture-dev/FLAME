"""Real loopback HTTP failures, without provider credentials or paid calls."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from time import perf_counter

import pytest

from app.modules.application.teaching import gateway


@contextmanager
def provider(monkeypatch, mode):
    calls = []
    release = Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            calls.append(self.rfile.read(int(self.headers['Content-Length'])))
            if mode == 'timeout':
                release.wait(3)
                return
            if mode == 'disconnect':
                self.connection.close()
                return
            self.send_response(503)
            self.send_header('Content-Length', '0')
            self.end_headers()

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    monkeypatch.setattr(gateway, 'RESPONSES_URL', f'http://127.0.0.1:{server.server_port}/responses')
    try:
        yield calls
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


@pytest.mark.parametrize('mode', ['timeout', 'disconnect', 'outage'])
def test_real_http_failure_is_bounded_and_safe(monkeypatch, mode):
    with provider(monkeypatch, mode) as calls:
        started = perf_counter()
        with pytest.raises(gateway.GatewayError) as error:
            gateway.OpenAIResponsesGateway('synthetic-key', 'synthetic-model', timeout_seconds=0.1).generate(
                [{'role': 'user', 'content': 'Synthetic question'}])
        assert error.value.code == 'provider_unavailable'
        assert len(calls) == 2
        assert perf_counter() - started < 3

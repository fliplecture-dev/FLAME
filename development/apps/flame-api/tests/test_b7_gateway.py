import httpx
import pytest
from app.modules.teaching.gateway import OpenAIResponsesGateway, GatewayError


def test_responses_adapter_bounds_request_and_retries_429(monkeypatch):
    original = httpx.Client
    calls = []
    def handle(request):
        calls.append(request)
        assert request.url == 'https://api.openai.com/v1/responses'
        assert request.headers['authorization'] == 'Bearer test-key'
        data = __import__('json').loads(request.content)
        assert data['store'] is False and data['tools'] == []
        assert data['tool_choice'] == 'none' and data['max_output_tokens'] == 300
        if len(calls) == 1:
            return httpx.Response(429)
        return httpx.Response(200, json={'status': 'completed', 'model': 'test-model',
            'output': [{'type': 'message', 'role': 'assistant', 'content': [
                {'type': 'output_text', 'text': 'Hello.'}]}],
            'usage': {'input_tokens': 10, 'output_tokens': 2}})
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original(
        transport=httpx.MockTransport(handle), **kwargs))
    answer = OpenAIResponsesGateway('test-key', 'test-model', max_output_tokens=300).generate(
        [{'role': 'user', 'content': 'Hello'}])
    assert answer.text == 'Hello.' and answer.input_tokens == 10
    assert len(calls) == 2


def test_responses_adapter_rejects_incomplete_output(monkeypatch):
    original = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
            'status': 'incomplete', 'output': []})), **kwargs))
    with pytest.raises(GatewayError) as exc:
        OpenAIResponsesGateway('test-key', 'test-model').generate([])
    assert exc.value.code == 'invalid_provider_output'


def test_responses_adapter_stops_after_two_timeouts(monkeypatch):
    original = httpx.Client
    calls = 0
    def timeout(request):
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timeout")
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original(
        transport=httpx.MockTransport(timeout), **kwargs))
    with pytest.raises(GatewayError) as exc:
        OpenAIResponsesGateway('test-key', 'test-model').generate([])
    assert exc.value.code == 'provider_unavailable'
    assert calls == 2


def test_responses_adapter_combines_text_parts_after_reasoning(monkeypatch):
    original = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
            'status': 'completed', 'model': 'test-model',
            'output': [{'type': 'reasoning', 'summary': []},
                       {'type': 'message', 'role': 'assistant', 'status': 'completed',
                        'content': [{'type': 'output_text', 'text': 'Hello'},
                                    {'type': 'output_text', 'text': ' world.'}]}],
            'usage': {'input_tokens': 10, 'output_tokens': 3}})), **kwargs))
    answer = OpenAIResponsesGateway('test-key', 'test-model').generate([])
    assert answer.text == 'Hello world.'


@pytest.mark.parametrize('content', [
    [{'type': 'refusal', 'refusal': 'Cannot comply'}],
    [{'type': 'output_text', 'text': 'Partial'}, {'type': 'refusal', 'refusal': 'No'}],
])
def test_responses_adapter_rejects_non_text_content(monkeypatch, content):
    original = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
            'status': 'completed', 'model': 'test-model',
            'output': [{'type': 'message', 'role': 'assistant', 'content': content}],
            'usage': {'input_tokens': 10, 'output_tokens': 3}})), **kwargs))
    with pytest.raises(GatewayError) as exc:
        OpenAIResponsesGateway('test-key', 'test-model').generate([])
    assert exc.value.code == 'invalid_provider_output'


def test_responses_adapter_does_not_retry_spend_limit(monkeypatch):
    original = httpx.Client
    calls = 0
    def handle(request):
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={'error': {'code': 'project_spend_limit_exceeded'}})
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original(
        transport=httpx.MockTransport(handle), **kwargs))
    with pytest.raises(GatewayError) as exc:
        OpenAIResponsesGateway('test-key', 'test-model').generate([])
    assert exc.value.code == 'provider_budget_exceeded'
    assert calls == 1

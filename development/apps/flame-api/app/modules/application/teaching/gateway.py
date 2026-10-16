"""Bounded OpenAI Responses transport; output text has no metadata authority."""
from dataclasses import dataclass
from time import sleep
import json
from time import monotonic
import httpx

RESPONSES_URL = "https://api.openai.com/v1/responses"

@dataclass(frozen=True)
class Generated:
    text: str
    model: str
    input_tokens: int
    output_tokens: int

class GatewayError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)

class UnconfiguredGateway:
    available = False
    def generate(self, messages: list[dict[str, str]]) -> Generated:
        raise GatewayError("provider_unavailable")

class OpenAIResponsesGateway:
    available = True
    def __init__(self, key: str, model: str, *, timeout_seconds: int = 12,
                 max_output_tokens: int = 1500, attempts: int = 2,
                 reasoning_effort: str | None = None):
        self.key = key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.attempts = max(1, min(2, attempts))
        self.reasoning_effort = reasoning_effort

    def generate_stream(self, messages, on_delta):
        """No transparent retries after visible output; final response remains authoritative."""
        payload = {"model": self.model, "input": messages, "store": False, "stream": True,
                   "tools": [], "tool_choice": "none", "max_output_tokens": self.max_output_tokens}
        headers = {"Authorization": "Bearer " + self.key, "Content-Type": "application/json"}
        started, text, completed = monotonic(), "", None
        try:
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                with client.stream("POST", RESPONSES_URL, headers=headers, json=payload) as response:
                    if response.status_code == 429:
                        response.read()
                        try:
                            code = response.json().get("error", {}).get("code")
                        except (ValueError, AttributeError, TypeError):
                            code = None
                        if code in {"project_spend_limit_exceeded", "organization_spend_limit_exceeded",
                                    "organization_usage_limit_exceeded", "credit_balance_exhausted"}:
                            raise GatewayError("provider_budget_exceeded")
                        raise GatewayError("provider_rate_limited")
                    if response.status_code != 200:
                        raise GatewayError("provider_unavailable")
                    for line in response.iter_lines():
                        if monotonic() - started > self.timeout_seconds:
                            raise GatewayError("provider_unavailable")
                        if len(line) > 100000:
                            raise GatewayError("invalid_provider_output")
                        if not line.startswith("data: "):
                            continue
                        event = json.loads(line[6:])
                        if event.get("type") == "response.output_text.delta":
                            delta = event.get("delta")
                            if not isinstance(delta, str) or len(text) + len(delta) > 10000:
                                raise GatewayError("invalid_provider_output")
                            text += delta
                            on_delta(delta)
                        elif event.get("type") == "response.completed":
                            completed = event.get("response")
                        elif event.get("type") in {"error", "response.failed", "response.incomplete"}:
                            raise GatewayError("provider_unavailable")
            if not isinstance(completed, dict) or completed.get("status") != "completed" or completed.get("error"):
                raise ValueError()
            output = completed["output"]
            messages_out = [item for item in output if item.get("type") == "message"]
            if len(messages_out) != 1 or any(item.get("type") not in {"message", "reasoning"} for item in output):
                raise ValueError()
            message = messages_out[0]
            if message.get("role") != "assistant" or not message.get("content") or any(part.get("type") != "output_text" for part in message["content"]):
                raise ValueError()
            final = "".join(part["text"] for part in message["content"])
            usage = completed["usage"]
            if final != text or not isinstance(completed.get("model"), str) or not completed["model"] or any(type(usage[k]) is not int or usage[k] < 0 for k in ("input_tokens", "output_tokens")) or usage["output_tokens"] > self.max_output_tokens:
                raise ValueError()
            return Generated(final, completed["model"], usage["input_tokens"], usage["output_tokens"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
            raise GatewayError("invalid_provider_output") from None

    def generate(self, messages: list[dict[str, str]]) -> Generated:
        payload = {"model": self.model, "input": messages, "store": False,
                   "tools": [], "tool_choice": "none",
                   "max_output_tokens": self.max_output_tokens}
        if self.reasoning_effort is not None:
            payload["reasoning"] = {"effort": self.reasoning_effort}
        headers = {"Authorization": "Bearer " + self.key, "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
            for attempt in range(self.attempts):
                try:
                    response = client.post(RESPONSES_URL, headers=headers, json=payload)
                except (httpx.TimeoutException, httpx.TransportError):
                    if attempt + 1 < self.attempts:
                        sleep(0.4)
                        continue
                    raise GatewayError("provider_unavailable") from None
                if response.status_code == 429:
                    try:
                        error_code = response.json().get("error", {}).get("code")
                    except (ValueError, TypeError, AttributeError):
                        error_code = None
                    if error_code in ("project_spend_limit_exceeded",
                                      "organization_spend_limit_exceeded",
                                      "organization_usage_limit_exceeded",
                                      "credit_balance_exhausted"):
                        raise GatewayError("provider_budget_exceeded")
                    if attempt + 1 < self.attempts:
                        sleep(0.4)
                        continue
                    raise GatewayError("provider_rate_limited")
                if response.status_code >= 500:
                    if attempt + 1 < self.attempts:
                        sleep(0.4)
                        continue
                    raise GatewayError("provider_unavailable")
                if response.status_code != 200:
                    raise GatewayError("provider_unavailable")
                try:
                    data = response.json()
                    if not isinstance(data, dict):
                        raise ValueError("invalid response envelope")
                    if data.get("status") != "completed" or data.get("error"):
                        if data.get("status") == "incomplete" and isinstance(data.get("incomplete_details"), dict) and data["incomplete_details"].get("reason") == "max_output_tokens":
                            raise GatewayError("provider_output_limit")
                        raise ValueError("response incomplete")
                    # Reasoning items may precede the assistant message. Reject tool,
                    # refusal, or other visible output rather than treating it as an answer.
                    output = data["output"]
                    if not isinstance(output, list) or any(not isinstance(item, dict) for item in output):
                        raise ValueError("invalid output")
                    messages = [item for item in output if item.get("type") == "message"]
                    if len(messages) != 1 or any(item.get("type") not in ("message", "reasoning")
                                                 for item in output):
                        raise ValueError("unexpected output item")
                    message = messages[0]
                    if message.get("role") != "assistant" or message.get("status") not in (None, "completed"):
                        raise ValueError("invalid assistant message")
                    parts = message.get("content")
                    if not isinstance(parts, list) or not parts or any(
                            not isinstance(part, dict) or part.get("type") != "output_text" or not isinstance(part.get("text"), str)
                            for part in parts):
                        raise ValueError("expected text output")
                    answer_text = "".join(part["text"] for part in parts)
                    usage = data["usage"]
                    if not isinstance(usage, dict) or not isinstance(data.get("model"), str) or not data["model"].strip():
                        raise ValueError("invalid response metadata")
                    input_tokens, output_tokens = usage["input_tokens"], usage["output_tokens"]
                    if type(input_tokens) is not int or type(output_tokens) is not int:
                        raise ValueError("invalid usage")
                    if input_tokens < 0 or output_tokens < 0 or output_tokens > self.max_output_tokens:
                        raise ValueError("usage outside bounds")
                    return Generated(answer_text, str(data["model"]), input_tokens, output_tokens)
                except (ValueError, KeyError, TypeError, IndexError):
                    raise GatewayError("invalid_provider_output") from None
        raise GatewayError("provider_unavailable")

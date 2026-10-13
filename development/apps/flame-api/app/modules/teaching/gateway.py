"""Bounded OpenAI Responses transport; output text has no metadata authority."""
from dataclasses import dataclass
from time import sleep
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
                 max_output_tokens: int = 1500):
        self.key = key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens

    def generate(self, messages: list[dict[str, str]]) -> Generated:
        payload = {"model": self.model, "input": messages, "store": False,
                   "tools": [], "tool_choice": "none",
                   "max_output_tokens": self.max_output_tokens}
        headers = {"Authorization": "Bearer " + self.key, "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
            for attempt in range(2):
                try:
                    response = client.post(RESPONSES_URL, headers=headers, json=payload)
                except (httpx.TimeoutException, httpx.TransportError):
                    if attempt == 0:
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
                    if attempt == 0:
                        sleep(0.4)
                        continue
                    raise GatewayError("provider_rate_limited")
                if response.status_code >= 500:
                    if attempt == 0:
                        sleep(0.4)
                        continue
                    raise GatewayError("provider_unavailable")
                if response.status_code != 200:
                    raise GatewayError("provider_unavailable")
                try:
                    data = response.json()
                    if data.get("status") != "completed" or data.get("error"):
                        raise ValueError("response incomplete")
                    # Reasoning items may precede the assistant message. Reject tool,
                    # refusal, or other visible output rather than treating it as an answer.
                    output = data["output"]
                    if not isinstance(output, list):
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
                            part.get("type") != "output_text" or not isinstance(part.get("text"), str)
                            for part in parts):
                        raise ValueError("expected text output")
                    answer_text = "".join(part["text"] for part in parts)
                    usage = data["usage"]
                    input_tokens, output_tokens = usage["input_tokens"], usage["output_tokens"]
                    if type(input_tokens) is not int or type(output_tokens) is not int:
                        raise ValueError("invalid usage")
                    if input_tokens < 0 or output_tokens < 0 or output_tokens > self.max_output_tokens:
                        raise ValueError("usage outside bounds")
                    return Generated(answer_text, str(data["model"]), input_tokens, output_tokens)
                except (ValueError, KeyError, TypeError, IndexError):
                    raise GatewayError("invalid_provider_output") from None
        raise GatewayError("provider_unavailable")

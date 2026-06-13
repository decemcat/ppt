from anthropic import Anthropic
from ppt_agent.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str = ""):
        self.client = Anthropic(api_key=api_key if api_key else None)

    def chat(self, messages: list[dict], model: str = "claude-sonnet-4-20250514", **kwargs) -> str:
        system = ""
        filtered_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                filtered_messages.append({"role": m["role"], "content": m["content"]})
        response = self.client.messages.create(
            model=model,
            system=system or None,
            messages=filtered_messages,
            **kwargs,
        )
        return response.content[0].text

    def chat_structured(self, messages: list[dict], response_model: type, model: str = "claude-sonnet-4-20250514", **kwargs) -> object:
        result = self.chat(messages, model, **kwargs)
        return response_model.model_validate_json(result)

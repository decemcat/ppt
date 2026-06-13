from anthropic import Anthropic
from ppt_agent.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str = "", base_url: str = ""):
        kwargs = {"api_key": api_key} if api_key else {}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = Anthropic(**kwargs)

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

    def chat_vision(self, text_prompt: str, images: list[bytes], model: str = "", **kwargs) -> str:
        import base64
        content: list[dict] = [{"type": "text", "text": text_prompt}]
        for img in images:
            b64 = base64.b64encode(img).decode()
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}})
        response = self.client.messages.create(
            model=model or "claude-sonnet-4-20250514",
            max_tokens=kwargs.pop("max_tokens", 500),
            messages=[{"role": "user", "content": content}],
            **kwargs,
        )
        return response.content[0].text

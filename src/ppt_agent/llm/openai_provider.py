from openai import OpenAI
from ppt_agent.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str = "", base_url: str = ""):
        kwargs = {"api_key": api_key} if api_key else {}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)

    def chat(self, messages: list[dict], model: str = "gpt-4o-mini", **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    def chat_structured(self, messages: list[dict], response_model: type, model: str = "gpt-4o-mini", **kwargs) -> object:
        response = self.client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=response_model,
            **kwargs,
        )
        return response.choices[0].message.parsed

    def chat_vision(self, text_prompt: str, images: list[bytes], model: str = "", **kwargs) -> str:
        import base64
        content: list[dict] = [{"type": "text", "text": text_prompt}]
        for img in images:
            b64 = base64.b64encode(img).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
        response = self.client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[{"role": "user", "content": content}],
            max_tokens=kwargs.pop("max_tokens", 500),
            **kwargs,
        )
        return response.choices[0].message.content or ""

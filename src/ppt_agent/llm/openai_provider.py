from openai import OpenAI
from ppt_agent.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str = ""):
        self.client = OpenAI(api_key=api_key if api_key else None)

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

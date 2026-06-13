from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], model: str = "", **kwargs) -> str:
        ...

    @abstractmethod
    def chat_structured(self, messages: list[dict], response_model: type, model: str = "", **kwargs) -> object:
        ...

    @abstractmethod
    def chat_vision(self, text_prompt: str, images: list[bytes], model: str = "", **kwargs) -> str:
        ...

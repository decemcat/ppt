from ppt_agent.config import Config
from ppt_agent.llm.base import LLMProvider
from ppt_agent.llm.openai_provider import OpenAIProvider
from ppt_agent.llm.anthropic_provider import AnthropicProvider


class ModelRouter:
    def __init__(self, config: Config):
        self.config = config
        self._providers: dict[str, LLMProvider] = {}

    def _get_provider(self, provider_name: str) -> LLMProvider:
        if provider_name not in self._providers:
            provider_config = self.config.llm.providers.get(provider_name)
            if not provider_config:
                raise ValueError(f"Unknown provider: {provider_name}")
            provider_type = provider_config.type or provider_name
            if provider_type in ("openai", "openai_compatible"):
                self._providers[provider_name] = OpenAIProvider(
                    api_key=provider_config.api_key,
                    base_url=provider_config.base_url,
                )
            elif provider_type == "anthropic":
                self._providers[provider_name] = AnthropicProvider(
                    api_key=provider_config.api_key,
                    base_url=provider_config.base_url,
                )
            else:
                raise ValueError(f"Unsupported provider type: {provider_type}")
        return self._providers[provider_name]

    def get_provider(self, provider_name: str) -> LLMProvider:
        return self._get_provider(provider_name)

    def get_model(self, route: str) -> tuple[LLMProvider, str]:
        tier = self.config.llm.routing.get(route, "fast")
        provider_name = self.config.llm.default_provider
        provider_config = self.config.llm.providers[provider_name]
        model = provider_config.deep_model if tier == "deep" else provider_config.fast_model
        return self._get_provider(provider_name), model

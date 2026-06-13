from ppt_agent.config import Config, LLMProviderConfig
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
            if provider_name == "openai":
                self._providers[provider_name] = OpenAIProvider(provider_config.api_key)
            elif provider_name == "anthropic":
                self._providers[provider_name] = AnthropicProvider(provider_config.api_key)
            else:
                raise ValueError(f"Unsupported provider: {provider_name}")
        return self._providers[provider_name]

    def get_model(self, route: str) -> tuple[LLMProvider, str]:
        """Get provider and model for a route key."""
        tier = self.config.llm.routing.get(route, "fast")
        provider_name = self.config.llm.default_provider
        provider_config = self.config.llm.providers[provider_name]
        model = provider_config.deep_model if tier == "deep" else provider_config.fast_model
        return self._get_provider(provider_name), model

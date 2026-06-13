from unittest.mock import patch, MagicMock
from ppt_agent.llm.router import ModelRouter
from ppt_agent.config import Config


class TestModelRouter:
    def test_router_creation(self):
        router = ModelRouter(Config())
        assert router is not None

    @patch("ppt_agent.llm.openai_provider.OpenAI")
    def test_get_model_for_daily(self, mock_openai):
        mock_openai.return_value = MagicMock()
        router = ModelRouter(Config())
        provider, model = router.get_model("daily_chat")
        assert provider is not None
        assert model is not None

    @patch("ppt_agent.llm.anthropic_provider.Anthropic")
    @patch("ppt_agent.llm.openai_provider.OpenAI")
    def test_anthropic_routing(self, mock_openai, mock_anthropic):
        mock_openai.return_value = MagicMock()
        mock_anthropic.return_value = MagicMock()
        config = Config()
        config.llm.default_provider = "anthropic"
        router = ModelRouter(config)
        provider, model = router.get_model("deep_reasoning")
        assert provider is not None
        assert model == "claude-thinking-4-20250514"

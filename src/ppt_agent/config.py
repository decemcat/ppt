from __future__ import annotations
from pathlib import Path
import yaml
from pydantic import BaseModel


class LLMProviderConfig(BaseModel):
    api_key: str = ""
    fast_model: str = "gpt-4o-mini"
    deep_model: str = "o3"


class LLMConfig(BaseModel):
    default_provider: str = "openai"
    providers: dict[str, LLMProviderConfig] = {
        "openai": LLMProviderConfig(),
        "anthropic": LLMProviderConfig(
            fast_model="claude-sonnet-4-20250514",
            deep_model="claude-thinking-4-20250514",
        ),
    }
    routing: dict[str, str] = {
        "daily_chat": "fast",
        "deep_reasoning": "deep",
        "adversarial": "dual",
    }


class Config(BaseModel):
    template_path: str = ""
    llm: LLMConfig = LLMConfig()


def load_config(path: str | None = None) -> Config:
    if path is None:
        config_dir = Path.home() / ".ppt-agent"
        path = str(config_dir / "config.yaml")
    config_path = Path(path)
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file {path}: {e}") from e
        if data is None:
            return Config()
        return Config.model_validate(data)
    return Config()

from __future__ import annotations
from pathlib import Path
import yaml
from pydantic import BaseModel, Field


class LLMProviderConfig(BaseModel):
    api_key: str = ""
    fast_model: str = "gpt-4o-mini"
    deep_model: str = "o3"


class LLMConfig(BaseModel):
    default_provider: str = "openai"
    providers: dict[str, LLMProviderConfig] = Field(
        default_factory=lambda: {
            "openai": LLMProviderConfig(),
            "anthropic": LLMProviderConfig(
                fast_model="claude-sonnet-4-20250514",
                deep_model="claude-thinking-4-20250514",
            ),
        }
    )
    routing: dict[str, str] = Field(
        default_factory=lambda: {
            "daily_chat": "fast",
            "deep_reasoning": "deep",
            "adversarial": "dual",
        }
    )


class KnowledgeConfig(BaseModel):
    max_age_days: int = 180
    auto_summarize: bool = True
    chroma_path: str = ""
    graph_path: str = ""

    @property
    def resolved_chroma_path(self) -> str:
        return self.chroma_path or str(Path.home() / ".ppt-agent" / "knowledge" / "chroma")

    @property
    def resolved_graph_path(self) -> str:
        return self.graph_path or str(Path.home() / ".ppt-agent" / "knowledge" / "graph" / "graph.json")


class ProxyConfig(BaseModel):
    enabled: bool = True
    http: str = "http://127.0.0.1:7890"
    https: str = "http://127.0.0.1:7890"


class Config(BaseModel):
    template_path: str = ""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)


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

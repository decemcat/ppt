import os
import tempfile
import yaml
from ppt_agent.config import Config, load_config


class TestConfig:
    def test_default_config(self):
        cfg = Config()
        assert cfg.llm.default_provider == "openai"

    def test_config_with_template(self):
        cfg = Config(template_path="/path/to/template.pptx")
        assert cfg.template_path == "/path/to/template.pptx"

    def test_load_config_from_file(self):
        data = {
            "llm": {
                "default_provider": "anthropic",
                "providers": {
                    "anthropic": {"api_key": "sk-test"},
                },
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            cfg = load_config(f.name)
            assert cfg.llm.default_provider == "anthropic"
            assert cfg.llm.providers["anthropic"].api_key == "sk-test"
        os.unlink(f.name)

from ppt_agent.config import Config, ImageGenConfig


class TestImageGen:
    def test_default_config(self):
        c = ImageGenConfig()
        assert c.provider == "auto"
        assert c.model == ""
        assert c.base_url == ""

    def test_image_gen_in_config(self):
        cfg = Config()
        assert cfg.image_gen.provider == "auto"
        assert cfg.image_gen.model == ""
        assert cfg.image_gen.base_url == ""

    def test_custom_model(self):
        c = ImageGenConfig(model="dall-e-3")
        assert c.model == "dall-e-3"

    def test_custom_base_url(self):
        c = ImageGenConfig(base_url="https://api.openai.com/v1/images/generations")
        assert c.base_url == "https://api.openai.com/v1/images/generations"

from ppt_agent.config import Config, ImageGenConfig


class TestImageGen:
    def test_default_config(self):
        c = ImageGenConfig()
        assert c.provider == "auto"
        assert c.model == ""

    def test_image_gen_in_config(self):
        cfg = Config()
        assert cfg.image_gen.provider == "auto"
        assert cfg.image_gen.model == ""

    def test_custom_model(self):
        c = ImageGenConfig(model="dall-e-3")
        assert c.model == "dall-e-3"

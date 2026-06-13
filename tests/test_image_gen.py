from ppt_agent.config import Config, ImageGenConfig


class TestImageGen:
    def test_default_disabled(self):
        c = ImageGenConfig()
        assert c.enabled is False

    def test_image_gen_in_config(self):
        cfg = Config()
        assert cfg.image_gen.enabled is False
        assert cfg.image_gen.provider == "auto"

    def test_enable_image_gen(self):
        c = ImageGenConfig(enabled=True, model="dall-e-3")
        assert c.enabled is True
        assert c.model == "dall-e-3"

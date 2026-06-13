import tempfile
from ppt_agent.style.profile import StyleProfile, ColorScheme, FontProfile, LayoutRatios
from ppt_agent.style.extractor import StyleExtractor


class TestStyleProfile:
    def test_default_profile(self):
        p = StyleProfile(name="test")
        assert p.colors.primary == "#1F4E79"
        assert p.fonts.title_font == "微软雅黑"

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = StyleProfile(name="my_style", colors=ColorScheme(primary="#FF0000"))
            profile.save(tmp)
            loaded = StyleProfile.load("my_style", tmp)
            assert loaded.colors.primary == "#FF0000"

    def test_list_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            StyleProfile(name="a").save(tmp)
            StyleProfile(name="b").save(tmp)
            names = StyleProfile.list_profiles(tmp)
            assert "a" in names
            assert "b" in names

    def test_load_missing_raises(self):
        try:
            StyleProfile.load("nonexistent", "/tmp/empty_dir_xyz_test")
            assert False, "Should have raised"
        except FileNotFoundError:
            pass


class TestStyleExtractor:
    def test_extractor_class_exists(self):
        assert hasattr(StyleExtractor, "extract")

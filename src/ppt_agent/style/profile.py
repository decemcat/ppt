from __future__ import annotations
from pathlib import Path
import yaml
from pydantic import BaseModel, Field


class ColorScheme(BaseModel):
    primary: str = "#1F4E79"
    secondary: str = "#2E75B6"
    accent: str = "#D6E4F0"
    background: str = "#FFFFFF"
    text_primary: str = "#1F4E79"
    text_secondary: str = "#333333"
    text_light: str = "#FFFFFF"


class FontProfile(BaseModel):
    title_font: str = "微软雅黑"
    title_size: int = 32
    subtitle_font: str = "微软雅黑"
    subtitle_size: int = 20
    body_font: str = "微软雅黑"
    body_size: int = 14
    caption_font: str = "微软雅黑"
    caption_size: int = 11


class LayoutRatios(BaseModel):
    title_height_ratio: float = 0.15
    content_margin_ratio: float = 0.08
    column_gap_ratio: float = 0.05
    element_spacing_ratio: float = 0.03


class StyleProfile(BaseModel):
    name: str = "default"
    colors: ColorScheme = Field(default_factory=ColorScheme)
    fonts: FontProfile = Field(default_factory=FontProfile)
    layout: LayoutRatios = Field(default_factory=LayoutRatios)
    source_file: str = ""

    def save(self, dir_path: str | None = None) -> str:
        save_dir = Path(dir_path or Path.home() / ".ppt-agent" / "styles")
        save_dir.mkdir(parents=True, exist_ok=True)
        path = save_dir / f"{self.name}.yaml"
        path.write_text(yaml.dump(self.model_dump(), allow_unicode=True, default_flow_style=False), encoding="utf-8")
        return str(path)

    @classmethod
    def load(cls, name: str, dir_path: str | None = None) -> "StyleProfile":
        load_dir = Path(dir_path or Path.home() / ".ppt-agent" / "styles")
        path = load_dir / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Style profile '{name}' not found at {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(**data)

    @classmethod
    def list_profiles(cls, dir_path: str | None = None) -> list[str]:
        load_dir = Path(dir_path or Path.home() / ".ppt-agent" / "styles")
        if not load_dir.exists():
            return []
        return sorted(p.stem for p in load_dir.glob("*.yaml"))

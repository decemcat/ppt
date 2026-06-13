from __future__ import annotations
import subprocess
import shutil
import tempfile
from pathlib import Path


class SlideCapture:
    @staticmethod
    def pptx_to_images(pptx_path: str, output_dir: str | None = None) -> list[str]:
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            return []
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                [soffice, "--headless", "--convert-to", "png", "--outdir", output_dir, pptx_path],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return []
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
        return sorted(str(p) for p in Path(output_dir).glob("*.png"))

    @staticmethod
    def is_available() -> bool:
        return (shutil.which("soffice") or shutil.which("libreoffice")) is not None

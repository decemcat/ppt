from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
from pptx.util import Inches
from ppt_agent.models import ArchDiagram


def _diagram_to_mermaid(diag: ArchDiagram) -> str:
    """Convert ArchDiagram to Mermaid flowchart syntax."""
    lines = ["graph TB"]
    for node in diag.nodes:
        if node.children:
            lines.append(f"    subgraph {node.id}[{node.label}]")
            for child in node.children:
                lines.append(f"        {child}[[{child}]]")
            lines.append("    end")
        else:
            lines.append(f"    {node.id}[{node.label}]")
    for edge in diag.edges:
        style = "-.->" if edge.style == "dashed" else "-->"
        label = f"|{edge.label}|" if edge.label else ""
        lines.append(f"    {edge.from_id} {style}{label} {edge.to_id}")
    return "\n".join(lines)


def render_as_image(diag: ArchDiagram, output_path: str) -> str:
    """Render ArchDiagram as PNG using Mermaid CLI.

    Returns path to generated PNG. Falls back to a placeholder if mermaid-cli unavailable.
    """
    mermaid_code = _diagram_to_mermaid(diag)
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as f:
            f.write(mermaid_code)
            mmd_path = f.name
        svg_path = mmd_path.replace(".mmd", ".svg")
        png_path = mmd_path.replace(".mmd", ".png")
        subprocess.run(
            ["mmdc", "-i", mmd_path, "-o", svg_path, "-w", "1200", "-H", "675"],
            capture_output=True, timeout=30,
        )
        if Path(svg_path).exists() and not Path(png_path).exists():
            import cairosvg
            cairosvg.svg2png(url=svg_path, write_to=png_path)
        if Path(png_path).exists():
            import shutil
            shutil.move(png_path, output_path)
            return output_path
    except (subprocess.TimeoutExpired, FileNotFoundError, ImportError):
        pass
    _create_placeholder_png(output_path)
    return output_path


def _create_placeholder_png(path: str):
    """Create a simple placeholder PNG when Mermaid render is unavailable."""
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (1200, 675), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((50, 300), "Architecture Diagram\n(Install mermaid-cli for rendering)", fill=(100, 100, 100))
        img.save(path)
    except ImportError:
        pass

from __future__ import annotations
import base64
import requests
from pathlib import Path
from ppt_agent.config import Config
from ppt_agent.llm.router import ModelRouter


class ImageGenerator:
    """Generate images using OpenAI DALL-E or compatible APIs."""

    def __init__(self, config: Config, router: ModelRouter):
        ig = config.image_gen
        if ig.provider != "auto":
            provider = router.get_provider(ig.provider)
            provider_config = config.llm.providers[ig.provider]
            model = ig.model or provider_config.fast_model
        else:
            provider, model = router.get_model("image_gen")
            provider_config = config.llm.providers[config.llm.default_provider]
        self.api_key = provider_config.api_key
        self.base_url = provider_config.base_url.rstrip("/") if provider_config.base_url else ""
        self.model = model

    def generate(self, prompt: str, size: str = "1024x1024", output_path: str | None = None) -> str:
        url = self.base_url + "/v1/images/generations" if self.base_url else "https://api.openai.com/v1/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "prompt": prompt, "n": 1, "size": size}
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            image_url = data["data"][0].get("url") or data["data"][0].get("b64_json")
            if image_url and output_path:
                if image_url.startswith("http"):
                    img_resp = requests.get(image_url, timeout=30)
                    img_resp.raise_for_status()
                    Path(output_path).write_bytes(img_resp.content)
                else:
                    Path(output_path).write_bytes(base64.b64decode(image_url))
                return output_path
            return image_url or ""
        except Exception:
            return ""

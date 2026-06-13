from __future__ import annotations
import json
import base64
from pathlib import Path
from ppt_agent.llm.base import LLMProvider


VISION_PROMPT = """你是PPT排版评审专家。请对以下幻灯片截图进行评审。

评分维度（0-10分）：
1. 布局平衡（layout_balance）：元素是否均衡分布？有无偏重或留白不当？
2. 文字密度（text_density）：文字量是否适中？是否过于拥挤或过于稀疏？
3. 配色一致性（color_consistency）：配色是否统一和谐？有无突兀颜色？
4. 视觉层级（visual_hierarchy）：标题/正文/图表的层级是否清晰？
5. 整洁度（cleanliness）：整体是否简洁专业？有无花哨装饰？

严格按以下JSON格式输出，不要输出其他内容：
{"layout_balance":0,"text_density":0,"color_consistency":0,"visual_hierarchy":0,"cleanliness":0,"overall":0,"issues":[]}"""


class VisionJudge:
    def __init__(self, provider: LLMProvider, model: str):
        self.provider = provider
        self.model = model

    def evaluate_slide(self, image_path: str) -> dict:
        try:
            return self._evaluate_with_api(image_path)
        except Exception:
            return {
                "layout_balance": 0, "text_density": 0, "color_consistency": 0,
                "visual_hierarchy": 0, "cleanliness": 0, "overall": 0, "issues": ["视觉评审失败"],
            }

    def _evaluate_with_api(self, image_path: str) -> dict:
        img_data = base64.b64encode(Path(image_path).read_bytes()).decode()
        ext = Path(image_path).suffix.lstrip(".") or "png"
        import openai
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{img_data}"}},
                ],
            }],
            max_tokens=500,
        )
        text = response.choices[0].message.content or ""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(text)

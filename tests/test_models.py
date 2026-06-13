import pytest
from pydantic import ValidationError
from ppt_agent.models import (
    ArchNode, ArchEdge, ArchDiagram,
    SlideContent, SlideFramework, PPTFramework
)


class TestArchDiagram:
    def test_node_creation(self):
        node = ArchNode(id="app", label="应用层", style="group")
        assert node.id == "app"
        assert node.label == "应用层"
        assert node.children == []

    def test_node_invalid_style(self):
        with pytest.raises(ValidationError):
            ArchNode(id="x", label="x", style="invalid")

    def test_edge_creation(self):
        edge = ArchEdge(from_id="app", to_id="db", label="gRPC")
        assert edge.from_id == "app"
        assert edge.to_id == "db"

    def test_diagram_creation(self):
        diag = ArchDiagram(
            type="layered",
            nodes=[
                ArchNode(id="app", label="应用层", children=["web", "api"]),
                ArchNode(id="data", label="数据层"),
            ],
            edges=[ArchEdge(from_id="app", to_id="data")],
        )
        assert diag.type == "layered"
        assert len(diag.nodes) == 2


class TestSlideFramework:
    def test_slide_content(self):
        slide = SlideContent(
            title="架构总览",
            slide_type="arch_diagram",
            diagram=ArchDiagram(
                type="layered", nodes=[ArchNode(id="a", label="A")], edges=[]
            ),
        )
        assert slide.title == "架构总览"

    def test_slide_text_content(self):
        slide = SlideContent(
            title="背景与痛点",
            slide_type="text",
            bullets=["痛点1", "痛点2", "痛点3"],
        )
        assert len(slide.bullets) == 3

    def test_image_prompt_default(self):
        slide = SlideContent(title="系统架构", slide_type="arch_diagram")
        assert slide.image_prompt == ""

    def test_image_prompt_set(self):
        slide = SlideContent(
            title="服务调用链",
            slide_type="text",
            image_prompt="A microservice architecture diagram showing API gateway, service mesh, and message queue",
        )
        assert "microservice" in slide.image_prompt

    def test_framework_creation(self):
        fw = SlideFramework(slides=[SlideContent(title="封面", slide_type="title")])
        assert len(fw.slides) == 1

    def test_ppt_framework(self):
        ppt = PPTFramework(
            title="AI训练平台方案",
            framework=SlideFramework(slides=[
                SlideContent(title="封面", slide_type="title"),
            ]),
        )
        assert ppt.title == "AI训练平台方案"

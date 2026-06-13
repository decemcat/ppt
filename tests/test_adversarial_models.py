from ppt_agent.adversarial.models import (
    Critique, ContestedPoint, DebateRound, DebateResult,
)
from ppt_agent.models import PPTFramework, SlideFramework, SlideContent


class TestAdversarialModels:
    def test_critique_creation(self):
        c = Critique(point="逻辑断层", severity="critical", suggestion="增加过渡页")
        assert c.severity == "critical"

    def test_contested_point(self):
        cp = ContestedPoint(
            critique=Critique(point="p", severity="important", suggestion="s"),
            defense="辩护理由",
            judge_verdict="undecided",
            reason="双方都有道理",
        )
        assert cp.judge_verdict == "undecided"

    def test_debate_round(self):
        r = DebateRound(round_number=1, judge_notes="test")
        assert r.round_number == 1
        assert len(r.critiques) == 0

    def test_debate_result(self):
        fw = PPTFramework(
            title="test",
            framework=SlideFramework(slides=[SlideContent(title="T", slide_type="title")]),
        )
        result = DebateResult(original_framework=fw, final_framework=fw, logic_score=75.0)
        assert result.logic_score == 75.0

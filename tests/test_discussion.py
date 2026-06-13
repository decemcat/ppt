from ppt_agent.adversarial.discussion import AdversarialDiscussion
from ppt_agent.adversarial.models import Critique, DebateResult
from ppt_agent.models import PPTFramework, SlideFramework, SlideContent
from ppt_agent.config import Config
from unittest.mock import MagicMock


def _make_discussion():
    disc = object.__new__(AdversarialDiscussion)
    disc.config = Config()
    disc.critic = MagicMock()
    disc.proponent = MagicMock()
    disc.judge = MagicMock()
    return disc


class TestDiscussionScoring:
    def test_score_no_critiques(self):
        disc = _make_discussion()
        score = disc._calculate_score([])
        assert score == 100.0

    def test_score_with_critical(self):
        disc = _make_discussion()
        critiques = [Critique(point="p", severity="critical", suggestion="s")]
        score = disc._calculate_score(critiques)
        assert score == 85.0

    def test_score_mixed(self):
        disc = _make_discussion()
        critiques = [
            Critique(point="p1", severity="critical", suggestion="s1"),
            Critique(point="p2", severity="important", suggestion="s2"),
            Critique(point="p3", severity="minor", suggestion="s3"),
        ]
        score = disc._calculate_score(critiques)
        assert score == 100 - 15 - 8 - 3

    def test_score_floor(self):
        disc = _make_discussion()
        critiques = [Critique(point=f"p{i}", severity="critical", suggestion=f"s{i}") for i in range(10)]
        score = disc._calculate_score(critiques)
        assert score == 0.0

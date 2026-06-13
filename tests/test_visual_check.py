from ppt_agent.quality.checker import SlideScore, VisualCheckResult


class TestVisualCheck:
    def test_slide_score_defaults(self):
        s = SlideScore(slide_index=0)
        assert s.overall == 0.0
        assert len(s.issues) == 0

    def test_visual_check_result(self):
        r = VisualCheckResult(passed=True, summary="ok", total_score=8.0)
        assert r.passed is True

    def test_check_result_with_scores(self):
        scores = [
            SlideScore(slide_index=0, overall=8.0),
            SlideScore(slide_index=1, overall=6.0, issues=["文字过密"]),
        ]
        r = VisualCheckResult(scores=scores, total_score=7.0, passed=True)
        assert len(r.scores) == 2

    def test_slide_capture_not_available(self):
        from ppt_agent.quality.slide_capture import SlideCapture
        assert isinstance(SlideCapture.is_available(), bool)

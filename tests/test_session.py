import json
import tempfile
from pathlib import Path
from ppt_agent.session import Session


class TestSession:
    def test_session_creation(self):
        session = Session(topic="AI训练平台")
        assert session.topic == "AI训练平台"
        assert session.session_id is not None
        assert len(session.messages) == 0

    def test_add_message(self):
        session = Session(topic="test")
        session.add_message("user", "你好")
        assert len(session.messages) == 1
        assert session.messages[0]["role"] == "user"

    def test_save_and_load(self, tmp_path):
        session = Session(topic="test", session_dir=str(tmp_path))
        session.add_message("user", "你好")
        session.add_message("assistant", "请说")
        path = session.save()
        loaded = Session.load(path)
        assert loaded.topic == "test"
        assert len(loaded.messages) == 2
        assert loaded.messages[1]["content"] == "请说"

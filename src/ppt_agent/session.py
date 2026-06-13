from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path


class Session:
    def __init__(self, topic: str, session_dir: str | None = None):
        self.session_id = str(uuid.uuid4())[:8]
        self.topic = topic
        self.created_at = datetime.now().isoformat()
        self.messages: list[dict] = []
        self.framework: dict | None = None
        self.session_dir = session_dir or str(Path.home() / ".ppt-agent" / "sessions")

    def add_message(self, role: str, content: str, metadata: dict | None = None):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
        })

    def save(self) -> str:
        path = Path(self.session_dir) / f"{self.created_at[:10]}_{self.session_id}"
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / "session.json"
        with open(file_path, "w") as f:
            json.dump({
                "session_id": self.session_id,
                "topic": self.topic,
                "created_at": self.created_at,
                "messages": self.messages,
                "framework": self.framework,
            }, f, ensure_ascii=False, indent=2)
        return str(file_path)

    @classmethod
    def load(cls, path: str) -> Session:
        with open(path) as f:
            data = json.load(f)
        session = cls(topic=data["topic"])
        session.session_id = data["session_id"]
        session.created_at = data["created_at"]
        session.messages = data["messages"]
        session.framework = data.get("framework")
        return session

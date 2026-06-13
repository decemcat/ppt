from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path


class Session:
    def __init__(
        self,
        topic: str,
        session_id: str | None = None,
        created_at: str | None = None,
        messages: list[dict] | None = None,
        framework: dict | None = None,
        template_path: str | None = None,
        session_dir: str | None = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.topic = topic
        self.created_at = created_at or datetime.now().isoformat()
        self.messages = messages or []
        self.framework = framework
        self.template_path = template_path
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
                "template_path": self.template_path,
            }, f, ensure_ascii=False, indent=2)
        return str(file_path)

    @classmethod
    def load(cls, path: str) -> Session:
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise ValueError(f"Failed to load session from {path}: {e}") from e
        return cls(
            topic=data["topic"],
            session_id=data["session_id"],
            created_at=data["created_at"],
            messages=data["messages"],
            framework=data.get("framework"),
            template_path=data.get("template_path"),
        )

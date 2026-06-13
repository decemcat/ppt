from __future__ import annotations
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.prompt import Prompt
from rich.text import Text
from rich import box
from threading import Lock
from contextlib import contextmanager
from datetime import datetime


class TaskStatus:
    pending = "⏳"
    running = "🔄"
    done = "✅"
    failed = "❌"


class TUI:
    def __init__(self, topic: str = ""):
        self.console = Console()
        self.tasks: dict[str, str] = {}  # name -> status
        self.logs: list[str] = []
        self.context_usage: str = "—"
        self._live: Live | None = None
        self._lock = Lock()

    def set_tasks(self, tasks: list[str]):
        with self._lock:
            self.tasks = {t: TaskStatus.pending for t in tasks}

    def task_start(self, name: str):
        with self._lock:
            if name in self.tasks:
                self.tasks[name] = TaskStatus.running
            self._refresh()

    def task_done(self, name: str):
        with self._lock:
            if name in self.tasks:
                self.tasks[name] = TaskStatus.done
            self._refresh()

    def task_fail(self, name: str):
        with self._lock:
            if name in self.tasks:
                self.tasks[name] = TaskStatus.failed
            self._refresh()

    def log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self.logs.append(f"[dim]{ts}[/dim] {message}")
            self._refresh()

    def set_context(self, info: str):
        with self._lock:
            self.context_usage = info
            self._refresh()

    def _build_right_panel(self) -> Panel:
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        table.add_column("icon", width=2)
        table.add_column("task", style="bold")
        for name, status in self.tasks.items():
            table.add_row(status, name)
        return Panel(table, title="Progress", border_style="blue")

    def _build_status_bar(self) -> Text:
        return Text(f"Context: {self.context_usage}", style="dim italic")

    def _build_layout(self) -> Layout:
        layout = Layout()
        layout.split(
            Layout(name="header", size=1),
            Layout(name="body"),
            Layout(name="status", size=1),
        )
        body_left = Panel(
            "\n".join(self.logs[-20:]) if self.logs else "等待开始...",
            title="Log", border_style="green",
        )
        body_right = self._build_right_panel()
        layout["body"].split_row(
            Layout(body_left, name="left", ratio=2),
            Layout(body_right, name="right", ratio=1),
        )
        layout["status"].update(
            Panel(self._build_status_bar(), box=box.SIMPLE, padding=(0, 1))
        )
        return layout

    def _refresh(self):
        if self._live and self._live.is_started:
            self._live.update(self._build_layout())

    @contextmanager
    def live_display(self):
        self._live = Live(self._build_layout(), console=self.console, refresh_per_second=4, screen=True)
        with self._live:
            yield
        self._live = None

    def ask(self, prompt_text: str = "> ") -> str:
        if self._live:
            self._live.stop()
        result = Prompt.ask(prompt_text)
        if self._live:
            self._live.start()
        return result

    def print(self, message: str):
        self.log(message)

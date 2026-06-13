from __future__ import annotations
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich import box
from threading import Lock
from datetime import datetime


class TaskStatus:
    pending = "⏳"
    running = "🔄"
    done = "✅"
    failed = "❌"


class TUI:
    def __init__(self):
        self.console = Console()
        self.tasks: dict[str, str] = {}
        self.logs: list[str] = []
        self.context_usage: str = "—"
        self._live: Live | None = None
        self._lock = Lock()

    def set_tasks(self, tasks: list[str]):
        with self._lock:
            self.tasks = {t: TaskStatus.pending for t in tasks}
        self._refresh()

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

    def _build_tasks_table(self) -> Table:
        table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
        table.add_column("", width=2)
        table.add_column("Progress", style="bold")
        for name, status in self.tasks.items():
            table.add_row(status, name)
        return table

    def _build_renderable(self):
        log_lines = (self.logs[-15:] if self.logs else ["等待开始..."])
        log_panel = Panel("\n".join(log_lines), title="Log", border_style="green")
        tasks_panel = Panel(self._build_tasks_table(), title="Progress", border_style="blue")
        from rich.columns import Columns
        return Columns([log_panel, tasks_panel])

    def _refresh(self):
        if self._live and self._live.is_started:
            self._live.update(self._build_renderable())

    def enter(self):
        self._live = Live(self._build_renderable(), console=self.console, refresh_per_second=4, transient=True)
        return self._live

    def leave(self):
        if self._live:
            self._live.stop()

    def print(self, message: str):
        if self._live and self._live.is_started:
            self._live.console.print(message)
        else:
            self.console.print(message)

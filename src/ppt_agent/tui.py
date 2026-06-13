from __future__ import annotations
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich import box
from datetime import datetime
import threading


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
        self._lock = threading.Lock()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

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

    def _make_table(self) -> Table:
        grid = Table.grid(padding=(0, 1))
        grid.add_column(style="bold")
        for name, status in self.tasks.items():
            grid.add_row(f"    {status}  {name}")
        recent = self.logs[-6:] if self.logs else ["准备中..."]
        log_block = "\n".join(recent)
        return Panel(grid, title=f"Progress  ·  {self.context_usage}  ·  {datetime.now().strftime('%H:%M:%S')}", border_style="blue")

    def _refresh(self):
        if self._live and self._running:
            self._live.update(self._make_table(), refresh=True)

    def enter(self):
        self._running = True
        self._live = Live(self._make_table(), console=self.console, refresh_per_second=4)
        self._live.start(refresh=True)

    def leave(self):
        self._running = False
        if self._live:
            self._live.stop()
            self._live = None


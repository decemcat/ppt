from __future__ import annotations
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
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

    def _make_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=1),
            Layout(name="body"),
        )
        tasks_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        tasks_table.add_column("", width=2)
        tasks_table.add_column("Task", style="bold")
        for name, status in self.tasks.items():
            tasks_table.add_row(status, name)
        log_text = "\n".join(self.logs[-30:]) if self.logs else "等待开始..."
        log_panel = Panel(log_text, title="Log", border_style="green")
        task_panel = Panel(tasks_table, title="Progress", border_style="blue")
        layout["header"].update(
            Panel(f"Context: {self.context_usage}", box=box.SIMPLE, padding=(0, 1))
        )
        layout["body"].split_row(
            Layout(log_panel, ratio=2),
            Layout(task_panel, ratio=1),
        )
        return layout

    def _refresh(self):
        if self._live and self._running:
            try:
                self._live.update(self._make_layout())
            except Exception:
                pass

    def enter(self):
        self._running = True
        self._live = Live(
            self._make_layout(),
            console=self.console,
            refresh_per_second=4,
            transient=False,
            screen=False,
        )
        self._live.start()

    def leave(self):
        self._running = False
        if self._live:
            try:
                self._live.stop()
            except Exception:
                pass
            self._live = None

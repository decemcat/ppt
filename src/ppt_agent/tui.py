from __future__ import annotations
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, RichLog, Input, ListView, ListItem, Label
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from textual import events
from threading import Lock
from datetime import datetime


class TaskItem(ListItem):
    def __init__(self, label: str):
        super().__init__()
        self.status = "⏳"
        self.label = label

    def compose(self) -> ComposeResult:
        yield Label(f"{self.status} {self.label}")


class TaskList(Vertical):
    def compose(self) -> ComposeResult:
        self._items: dict[str, TaskItem] = {}

    def set_tasks(self, tasks: list[str]):
        self._items = {}
        self.remove_children()
        for t in tasks:
            item = TaskItem(t)
            self._items[t] = item
            self.mount(item)

    def task_start(self, name: str):
        if name in self._items:
            self._items[name].status = "🔄"
            self._items[name].query_one(Label).update(f"🔄 {name}")

    def task_done(self, name: str):
        if name in self._items:
            self._items[name].status = "✅"
            self._items[name].query_one(Label).update(f"✅ {name}")

    def task_fail(self, name: str):
        if name in self._items:
            self._items[name].status = "❌"
            self._items[name].query_one(Label).update(f"❌ {name}")


class PPTTUI(App):
    CSS = """
    Horizontal { height: 1fr; }
    #left { width: 2fr; border: solid green; }
    #right { width: 1fr; border: solid blue; }
    #right > Vertical { padding: 1; }
    #logs { height: 1fr; }
    #tasks { height: auto; }
    #input_container { height: 3; border: solid $accent; }
    #context { height: 1; background: $panel; }
    Input { width: 100%; }
    """

    input_text: reactive[str] = reactive("")

    def __init__(self):
        super().__init__()
        self._log_messages: list[str] = []
        self._external_ready = Lock()
        self._external_ready.acquire()
        self._input_value: str = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(id="context", markup=False)
        with Horizontal():
            with Container(id="left"):
                yield RichLog(id="logs", markup=True, highlight=True)
            with Container(id="right"):
                yield TaskList(id="tasks")
        yield Input(id="input", placeholder="输入你的想法... (/done 结束)")
        yield Footer()

    def on_mount(self):
        label = self.query_one("#context", Label)
        label.update("Context: —")
        self.query_one("#tasks", TaskList)
        self._external_ready.release()

    def log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_messages.append(f"[dim]{ts}[/dim] {message}")
        try:
            logs = self.query_one("#logs", RichLog)
            logs.write(f"{message}")
        except Exception:
            pass

    def set_context(self, info: str):
        try:
            self.query_one("#context", Label).update(f"Context: {info}")
        except Exception:
            pass

    def set_tasks(self, tasks: list[str]):
        try:
            self.query_one("#tasks", TaskList).set_tasks(tasks)
        except Exception:
            pass

    def task_start(self, name: str):
        try:
            self.query_one("#tasks", TaskList).task_start(name)
        except Exception:
            pass

    def task_done(self, name: str):
        try:
            self.query_one("#tasks", TaskList).task_done(name)
        except Exception:
            pass

    def task_fail(self, name: str):
        try:
            self.query_one("#tasks", TaskList).task_fail(name)
        except Exception:
            pass

    def on_input_submitted(self, event: Input.Submitted):
        self._input_value = event.value
        self.query_one("#input", Input).value = ""

    def wait_ready(self, timeout: float = 5.0):
        self._external_ready.acquire(timeout=timeout)
        self._external_ready = Lock()

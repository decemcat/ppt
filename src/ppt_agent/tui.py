from __future__ import annotations
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, RichLog, Input, Static
from textual.containers import Horizontal, Vertical
from textual.worker import get_current_worker
from datetime import datetime
import queue


class TaskState:
    pending = "⏳"
    running = "🔄"
    done = "✅"
    failed = "❌"


class PPTTUI(App):
    CSS = """
    #context { height: 1; background: $panel; padding: 0 1; }
    #main { height: 1fr; }
    #left { width: 2fr; border: solid green; }
    #right { width: 1fr; border: solid blue; padding: 1; }
    #logs { height: 1fr; }
    #task_list { height: auto; }
    #input { dock: bottom; height: 3; border: solid $accent; }
    .task_label { padding: 0 1; }
    """

    def __init__(self, input_queue: queue.Queue, topic: str, template_path: str | None = None, style_name: str | None = None):
        super().__init__()
        self.input_queue = input_queue
        self.topic = topic
        self.template_path = template_path
        self.style_name = style_name
        self._tasks: dict[str, tuple[str, Static]] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="context")
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield RichLog(id="logs", markup=True, highlight=True)
            with Vertical(id="right"):
                yield Vertical(id="task_list")
        yield Input(id="input", placeholder="输入你的想法... (/done 结束)")
        yield Footer()

    def on_mount(self):
        self.query_one("#context", Static).update("Context: —")
        from ppt_agent.orchestrator import orchestrator_task
        self.run_worker(orchestrator_task(self), exclusive=True, thread=True)

    def on_input_submitted(self, event: Input.Submitted):
        self.input_queue.put(event.value)
        self.query_one("#input", Input).value = ""

    def ui_log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.call_from_thread(self._do_log, ts, message)

    def _do_log(self, ts: str, message: str):
        self.query_one("#logs", RichLog).write(f"[dim]{ts}[/dim] {message}")

    def ui_context(self, info: str):
        self.call_from_thread(self._do_context, info)

    def _do_context(self, info: str):
        self.query_one("#context", Static).update(f"Context: {info}")

    def ui_init_tasks(self, tasks: list[str]):
        self.call_from_thread(self._do_init_tasks, tasks)

    def _do_init_tasks(self, tasks: list[str]):
        container = self.query_one("#task_list", Vertical)
        container.remove_children()
        self._tasks.clear()
        for t in tasks:
            label = Static(f"{TaskState.pending}  {t}", classes="task_label")
            container.mount(label)
            self._tasks[t] = (TaskState.pending, label)

    def ui_task_start(self, name: str):
        self.call_from_thread(self._do_task_start, name)

    def _do_task_start(self, name: str):
        if name in self._tasks:
            self._tasks[name] = (TaskState.running, self._tasks[name][1])
            self._tasks[name][1].update(f"{TaskState.running}  {name}")

    def ui_task_done(self, name: str):
        self.call_from_thread(self._do_task_done, name)

    def _do_task_done(self, name: str):
        if name in self._tasks:
            self._tasks[name] = (TaskState.done, self._tasks[name][1])
            self._tasks[name][1].update(f"{TaskState.done}  {name}")

    def ui_task_fail(self, name: str):
        self.call_from_thread(self._do_task_fail, name)

    def _do_task_fail(self, name: str):
        if name in self._tasks:
            self._tasks[name] = (TaskState.failed, self._tasks[name][1])
            self._tasks[name][1].update(f"{TaskState.failed}  {name}")

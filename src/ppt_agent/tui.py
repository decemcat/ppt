from __future__ import annotations
from textual.app import App, ComposeResult
from textual.widgets import RichLog, Input, Static
from textual.containers import Horizontal, Vertical, Container
from datetime import datetime
import queue
import threading


SENTINEL = "__QUIT__"


class PPTTUI(App):
    CSS = """
    Screen { layout: vertical; background: #0d1117; }
    #main { height: 1fr; }
    #left { width: 2fr; background: #0d1117; }
    #right { width: 1fr; background: #161b22; padding: 1; }
    #logs { height: 1fr; background: #0d1117; padding: 0 1; }
    #input_area { background: #0d1117; padding: 1; height: auto; }
    #input { width: 100%; height: 3; padding: 1; background: #161b22; border: none; }
    Input:focus { border: none; }
    #right_title { padding: 1 0 0 0; color: $text-muted; text-style: bold; }
    #task_desc { padding: 0 0 1 0; color: $text; }
    #stat_block { padding: 1 0; }
    #todo_title { padding: 1 0 0 0; color: $text-muted; text-style: bold; }
    #todo_list { padding: 0; }
    #status_bar { height: 1; padding: 0 1; background: #010409; color: $text-muted; }
    """

    BINDINGS = [("ctrl+q", "quit", "退出")]

    def __init__(self, input_queue: queue.Queue, topic: str = "", template_path: str | None = None, style_name: str | None = None):
        super().__init__()
        self.input_queue = input_queue
        self.topic = topic
        self.template_path = template_path
        self.style_name = style_name
        self._tasks: dict[str, tuple[bool, Static]] = {}
        self._stop_event = threading.Event()
        self._tokens: int = 0
        self._ctx_pct: int = 0
        self._model: str = "—"

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield RichLog(id="logs", markup=True, highlight=True, wrap=True)
                yield Container(Input(id="input", placeholder="输入... (/done 结束)"), id="input_area")
            with Vertical(id="right"):
                yield Static("Task", id="right_title")
                yield Static("等待开始...", id="task_desc")
                yield Container(
                    Static("Tokens: 0", id="stat_tokens"),
                    Static("Context: —%", id="stat_context"),
                    id="stat_block",
                )
                yield Static("Todo", id="todo_title")
                yield Vertical(id="todo_list")
        yield Static(id="status_bar")

    def on_mount(self):
        self._update_status_bar()
        self.query_one("#input", Input).focus()
        from ppt_agent.orchestrator import orchestrator_task
        t = threading.Thread(target=orchestrator_task(self), daemon=True)
        t.start()

    def on_unmount(self):
        self._stop_event.set()
        try:
            self.input_queue.put_nowait(SENTINEL)
        except queue.Full:
            pass

    def action_quit(self):
        self._stop_event.set()
        try:
            self.input_queue.put_nowait(SENTINEL)
        except queue.Full:
            pass
        self.exit()

    def on_input_submitted(self, event: Input.Submitted):
        self.input_queue.put(event.value)
        inp = self.query_one("#input", Input)
        inp.value = ""
        inp.focus()

    def get_input(self, timeout: float = 0.5) -> str | None:
        while not self._stop_event.is_set():
            try:
                return self.input_queue.get(timeout=timeout)
            except queue.Empty:
                continue
        return None

    def _update_status_bar(self):
        self.query_one("#status_bar", Static).update(
            f" 模型: {self._model}  |  Tokens: {self._tokens}  |  上下文: {self._ctx_pct}%  |  /done 结束讨论  |  /framework 查看框架  |  Ctrl+Q 退出"
        )

    def ui_log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.call_from_thread(self._do_log, ts, message)

    def _do_log(self, ts: str, message: str):
        self.query_one("#logs", RichLog).write(f"[dim]{ts}[/dim] {message}")

    def ui_model(self, name: str):
        self._model = name
        self.call_from_thread(self._update_status_bar)

    def ui_tokens(self, count: int):
        self._tokens = count
        self.call_from_thread(self._do_tokens)

    def _do_tokens(self):
        self.query_one("#stat_tokens", Static).update(f"Tokens: {self._tokens}")
        self._update_status_bar()

    def ui_context_pct(self, pct: int):
        self._ctx_pct = pct
        self.call_from_thread(self._do_context_pct)

    def _do_context_pct(self):
        self.query_one("#stat_context", Static).update(f"Context: {self._ctx_pct}%")
        self._update_status_bar()

    def ui_task_desc(self, text: str):
        self.call_from_thread(self._do_task_desc, text)

    def _do_task_desc(self, text: str):
        self.query_one("#task_desc", Static).update(text)

    def ui_init_tasks(self, tasks: list[str]):
        self.call_from_thread(self._do_init_tasks, tasks)

    def _do_init_tasks(self, tasks: list[str]):
        container = self.query_one("#todo_list", Vertical)
        container.remove_children()
        self._tasks.clear()
        for t in tasks:
            label = Static(f"  [ ]  {t}")
            container.mount(label)
            self._tasks[t] = (False, label)

    def ui_task_done(self, name: str):
        self.call_from_thread(self._do_task_done, name)

    def _do_task_done(self, name: str):
        if name in self._tasks:
            self._tasks[name] = (True, self._tasks[name][1])
            self._tasks[name][1].update(f"  [x]  {name}")

    def ui_task_running(self, name: str):
        self.call_from_thread(self._do_task_running, name)

    def _do_task_running(self, name: str):
        if name in self._tasks:
            self._tasks[name][1].update(f"  [·]  {name}")

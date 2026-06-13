from __future__ import annotations
from textual.app import App, ComposeResult
from textual.widgets import RichLog, Static, TextArea
from textual.containers import Horizontal, Vertical, Container
from textual.binding import Binding
from rich.markdown import Markdown as RichMarkdown
from rich.text import Text
import queue
import threading


SENTINEL = "__QUIT__"
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class PPTTUI(App):
    CSS = """
    Screen { layout: vertical; background: #0d1117; }
    #main { height: 1fr; }
    #left { width: 2fr; background: #0d1117; }
    #right { width: 1fr; background: #161b22; padding: 1; }
    #logs { height: 1fr; background: #0d1117; padding: 0 1; }
    #busy { background: #0d1117; padding: 0 1 0 1; color: $warning; height: 1; }
    #input_area { background: #0d1117; padding: 1; height: auto; }
    #input { width: 100%; min-height: 2; max-height: 10; padding: 0 1; background: #161b22; border: none; }
    TextArea:focus { border: none; }
    #right_title { padding: 1 0 0 0; color: $text-muted; text-style: bold; }
    #task_desc { padding: 0 0 1 0; color: $text; }
    #stat_block { padding: 1 0; }
    #todo_title { padding: 1 0 0 0; color: $text-muted; text-style: bold; }
    #todo_list { padding: 0; }
    #sub_title { padding: 1 0 0 0; color: $text-muted; text-style: bold; }
    #sub_list { padding: 0; }
    #status_bar { height: 1; padding: 0 1; background: #010409; color: $text-muted; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("escape", "focus_input", "Focus input", show=False),
    ]

    def action_focus_input(self):
        self.query_one("#input", TextArea).focus()

    def __init__(self, input_queue: queue.Queue):
        super().__init__()
        self.input_queue = input_queue
        self._busy_text: str = ""
        self._tasks: dict[str, tuple[bool, Static]] = {}
        self._subagents: dict[str, Static] = {}
        self._stop_event = threading.Event()
        self._tokens: int = 0
        self._ctx_pct: int = 0
        self._model: str = "—"

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield RichLog(id="logs", markup=True, highlight=True, wrap=True)
                yield Static("", id="busy")
                yield Container(
                    TextArea("", id="input", language=None, show_line_numbers=False, tab_behavior="focus"),
                    id="input_area",
                )
            with Vertical(id="right"):
                yield Static("Task", id="right_title")
                yield Static("Waiting...", id="task_desc")
                yield Container(
                    Static("Tokens: 0", id="stat_tokens"),
                    Static("Context: —%", id="stat_context"),
                    id="stat_block",
                )
                yield Static("Todo", id="todo_title")
                yield Vertical(id="todo_list")
                yield Static("Subagents", id="sub_title")
                yield Vertical(id="sub_list")
        yield Static(id="status_bar")

    def on_mount(self):
        self._update_status_bar()
        self.query_one("#input", TextArea).focus()
        self._dot_frame = 0
        self.set_interval(0.08, self._animate_busy)
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

    def on_text_area_changed(self, event: TextArea.Changed):
        if event.text_area.id != "input":
            return
        text = event.text_area.text
        if "\n" in text:
            lines = text.split("\n")
            for line in lines[:-1]:
                if line.strip():
                    self.input_queue.put(line.strip())
            event.text_area.text = ""

    def get_input(self, timeout: float = 0.5) -> str | None:
        while not self._stop_event.is_set():
            try:
                return self.input_queue.get(timeout=timeout)
            except queue.Empty:
                continue
        return None

    def _update_status_bar(self):
        self.query_one("#status_bar", Static).update(
            f" Model: {self._model}  |  Tokens: {self._tokens}  |  Context: {self._ctx_pct}%  |  Enter: send  |  Shift+Enter: newline  |  /done end  |  Ctrl+Q quit"
        )

    def _animate_busy(self):
        if not self._busy_text:
            self.query_one("#busy", Static).update("")
            return
        self._dot_frame = (self._dot_frame + 1) % len(SPINNER_FRAMES)
        self.query_one("#busy", Static).update(f"  {SPINNER_FRAMES[self._dot_frame]} {self._busy_text}")

    def ui_busy(self, text: str):
        self._busy_text = text
        if not text:
            self.call_from_thread(lambda: self.query_one("#busy", Static).update(""))

    def ui_log(self, message: str):
        self.call_from_thread(self._do_log, message)

    def _do_log(self, message: str):
        self.query_one("#logs", RichLog).write(message)

    def ui_agent(self, message: str):
        self.call_from_thread(self._do_agent, message)

    def _do_agent(self, message: str):
        log = self.query_one("#logs", RichLog)
        try:
            md = RichMarkdown(message)
            log.write("")
            log.write(md)
            log.write("")
        except Exception:
            log.write(message)

    def ui_user(self, message: str):
        self.call_from_thread(self._do_user, message)

    def _do_user(self, message: str):
        log = self.query_one("#logs", RichLog)
        t = Text()
        t.append("\n▌ ", style="bold cyan")
        t.append(message, style="cyan")
        log.write(t)

    def ui_confirm(self, message: str):
        self.call_from_thread(self._do_confirm, message)

    def _do_confirm(self, message: str):
        log = self.query_one("#logs", RichLog)
        t = Text()
        t.append("\n▌ ", style="bold yellow")
        t.append(message, style="yellow")
        log.write(t)

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

    def ui_subagent_add(self, name: str, task: str):
        self.call_from_thread(self._do_subagent_add, name, task)

    def _do_subagent_add(self, name: str, task: str):
        label = Static(f"  [·]  {name}: {task}")
        self.query_one("#sub_list", Vertical).mount(label)
        self._subagents[name] = label

    def ui_subagent_done(self, name: str):
        self.call_from_thread(self._do_subagent_done, name)

    def _do_subagent_done(self, name: str):
        if name in self._subagents:
            old_text = self._subagents[name].renderable
            self._subagents[name].update(f"  [x]  {old_text.replace('  [·]  ', '')}")

    def ui_subagent_remove(self, name: str):
        self.call_from_thread(self._do_subagent_remove, name)

    def _do_subagent_remove(self, name: str):
        if name in self._subagents:
            self._subagents[name].remove()
            del self._subagents[name]

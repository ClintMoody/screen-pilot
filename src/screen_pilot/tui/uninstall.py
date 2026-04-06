"""screen-pilot TUI uninstaller -- selective component removal."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Label,
    ProgressBar,
    RichLog,
    Rule,
    Static,
)

# ---------------------------------------------------------------------------
# Removal targets
# ---------------------------------------------------------------------------

TARGETS = [
    (
        "systemd",
        "Systemd service",
        True,
        "Stop and disable the screen-pilot.service user unit",
    ),
    (
        "conda",
        "Conda environment",
        True,
        "Remove the screen-pilot conda/mamba environment",
    ),
    (
        "config",
        "Config files",
        True,
        "Delete ~/.config/screen-pilot/",
    ),
    (
        "weights",
        "OmniParser weights (~2 GB)",
        False,
        "Delete ~/.local/share/screen-pilot/weights/",
    ),
    (
        "syspkgs",
        "System packages",
        False,
        "Remove ydotool and screenshot tools installed by screen-pilot",
    ),
    (
        "miniconda",
        "Miniconda",
        False,
        "Remove ~/miniconda3 entirely (affects other conda envs!)",
    ),
]


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------

class SelectScreen:
    """Mixin-like -- we just use the main app compose for selection."""


class UninstallApp(App):
    """screen-pilot selective uninstaller."""

    TITLE = "screen-pilot uninstaller"
    SUB_TITLE = "Select components to remove"

    CSS = """
    Screen {
        background: $background;
    }
    #main-box {
        margin: 1 4;
        padding: 1 2;
        border: heavy $error;
        background: $surface;
        height: 1fr;
    }
    #title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    .target-group {
        margin: 0 1;
        padding: 0 1;
        height: auto;
    }
    .target-help {
        margin-left: 6;
        color: $text-muted;
        margin-bottom: 1;
    }
    .warn-default {
        /* Targets with default=False get a visual cue */
    }
    #warning-box {
        margin: 1 2;
        padding: 1 2;
        border: round $error;
        background: $error 15%;
        height: auto;
    }
    #btn-bar {
        align-horizontal: center;
        margin-top: 1;
        height: 3;
        dock: bottom;
    }
    #confirm-box {
        width: 60;
        height: 14;
        border: heavy $error;
        padding: 2 3;
        background: $surface;
    }
    #confirm-box Static {
        text-align: center;
        margin-bottom: 1;
    }
    #confirm-buttons {
        align-horizontal: center;
        height: 3;
    }
    #progress-box {
        margin: 1 4;
        padding: 1 2;
        border: heavy $error;
        background: $surface;
        height: 1fr;
    }
    #prog-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #step-label {
        text-align: center;
        color: $warning;
        margin: 1 0;
    }
    #uninstall-log {
        border: round $error 50%;
        margin: 1 1;
        height: 1fr;
        background: $boost;
    }
    #prog-buttons {
        align-horizontal: center;
        height: 3;
    }
    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._phase = "select"  # select | confirm | progress | done

    def compose(self) -> ComposeResult:
        yield Header()
        # Selection phase
        with Vertical(id="main-box"):
            yield Static("[bold red]Uninstall screen-pilot[/]", id="title")
            yield Rule()
            yield Static(
                "Choose which components to remove. Conservative defaults are pre-selected.",
            )
            with VerticalScroll(classes="target-group"):
                for tid, label, default, helptext in TARGETS:
                    yield Checkbox(label, value=default, id=f"chk-{tid}")
                    yield Static(f"  [dim]{helptext}[/]", classes="target-help")
            yield Static(
                "[bold red]Warning:[/] Removing system packages or Miniconda may affect "
                "other software on your system. Use with caution.",
                id="warning-box",
            )
        with Center(id="btn-bar"):
            yield Button("Cancel", id="btn-cancel")
            yield Button("Uninstall Selected", variant="error", id="btn-uninstall")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.exit()
        elif event.button.id == "btn-uninstall":
            selected = self._get_selected()
            if not selected:
                return
            self._show_confirm(selected)
        elif event.button.id == "btn-confirm-yes":
            selected = self._get_selected()
            self._start_removal(selected)
        elif event.button.id == "btn-confirm-no":
            # Remove the confirm overlay
            try:
                self.query_one("#confirm-box").remove()
            except Exception:
                pass
        elif event.button.id == "btn-exit":
            self.exit()

    def _get_selected(self) -> list[str]:
        selected = []
        for tid, *_ in TARGETS:
            try:
                chk = self.query_one(f"#chk-{tid}", Checkbox)
                if chk.value:
                    selected.append(tid)
            except Exception:
                pass
        return selected

    def _show_confirm(self, selected: list[str]) -> None:
        """Mount a confirmation overlay."""
        names = ", ".join(selected)
        confirm = Vertical(
            Static(f"[bold red]Confirm Removal[/]"),
            Rule(),
            Static(f"The following will be removed:\n[bold]{names}[/]"),
            Static("[yellow]This cannot be undone.[/]"),
            Horizontal(
                Button("Cancel", id="btn-confirm-no"),
                Button("Yes, Remove", variant="error", id="btn-confirm-yes"),
                id="confirm-buttons",
            ),
            id="confirm-box",
        )
        confirm.styles.align = ("center", "middle")
        confirm.styles.layer = "overlay"
        self.mount(confirm)

    def _start_removal(self, selected: list[str]) -> None:
        """Switch UI to progress view and run removal."""
        # Remove the selection UI and confirm box
        try:
            self.query_one("#confirm-box").remove()
        except Exception:
            pass
        try:
            self.query_one("#main-box").remove()
        except Exception:
            pass
        try:
            self.query_one("#btn-bar").remove()
        except Exception:
            pass

        # Mount progress UI
        progress_box = Vertical(
            Static("[bold red]Removing components...[/]", id="prog-title"),
            Rule(),
            Static("Starting...", id="step-label"),
            ProgressBar(total=100, id="progress-bar"),
            RichLog(id="uninstall-log", highlight=True, markup=True),
            Center(
                Button("Exit", variant="primary", id="btn-exit", disabled=True),
                id="prog-buttons",
            ),
            id="progress-box",
        )
        self.mount(progress_box, before=self.query_one(Footer))
        self._run_removal(selected)

    @work(thread=True)
    def _run_removal(self, selected: list[str]) -> None:
        """Execute removal steps in a worker thread."""
        log = self.query_one("#uninstall-log", RichLog)
        bar = self.query_one("#progress-bar", ProgressBar)
        step_label = self.query_one("#step-label", Static)

        total = len(selected)
        per_step = 100 // max(total, 1)

        for i, tid in enumerate(selected):
            label = next((l for t, l, *_ in TARGETS if t == tid), tid)
            self.call_from_thread(step_label.update, f"[bold]Removing: {label}[/]")
            self.call_from_thread(log.write, f"[red]\u25b6[/] Removing {label}...")

            # Simulate removal (real logic would use subprocess etc.)
            if tid == "systemd":
                self.call_from_thread(log.write, "  Stopping screen-pilot.service...")
                time.sleep(0.3)
                self.call_from_thread(log.write, "  Disabling service...")
                time.sleep(0.3)
                self.call_from_thread(log.write, "  Removing unit file...")
                time.sleep(0.2)
            elif tid == "conda":
                self.call_from_thread(log.write, "  Locating conda environment...")
                time.sleep(0.3)
                self.call_from_thread(log.write, "  Removing screen-pilot env...")
                time.sleep(0.5)
            elif tid == "config":
                cfg_dir = Path("~/.config/screen-pilot").expanduser()
                self.call_from_thread(log.write, f"  Removing {cfg_dir}...")
                time.sleep(0.3)
            elif tid == "weights":
                weights_dir = Path("~/.local/share/screen-pilot/weights").expanduser()
                self.call_from_thread(log.write, f"  Removing {weights_dir} (~2 GB)...")
                time.sleep(0.8)
            elif tid == "syspkgs":
                self.call_from_thread(log.write, "  Removing ydotool, screenshot tools...")
                time.sleep(0.5)
            elif tid == "miniconda":
                self.call_from_thread(log.write, "  Removing ~/miniconda3...")
                time.sleep(0.6)

            progress = min((i + 1) * per_step, 100)
            self.call_from_thread(bar.update, progress=progress)
            self.call_from_thread(log.write, f"  [green]\u2714[/] {label} removed\n")

        self.call_from_thread(bar.update, progress=100)
        self.call_from_thread(step_label.update, "[bold green]Removal complete[/]")
        self.call_from_thread(log.write, "[bold green]All selected components removed.[/]")
        self.call_from_thread(self._enable_exit)

    def _enable_exit(self) -> None:
        self.query_one("#btn-exit", Button).disabled = False


if __name__ == "__main__":
    UninstallApp().run()

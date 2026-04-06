"""screen-pilot interactive TUI installer -- Textual wizard."""

from __future__ import annotations

import asyncio
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import Screen
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
# System detection helpers
# ---------------------------------------------------------------------------

def _detect_session_type() -> str:
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session:
        return session.capitalize()
    if os.environ.get("WAYLAND_DISPLAY"):
        return "Wayland"
    if os.environ.get("DISPLAY"):
        return "X11"
    return "Unknown"


def _detect_gpu() -> str:
    try:
        out = subprocess.check_output(
            ["lspci"], stderr=subprocess.DEVNULL, text=True, timeout=5,
        )
        for line in out.splitlines():
            low = line.lower()
            if "vga" in low or "3d" in low or "display" in low:
                # Take the description after the colon
                parts = line.split(": ", 1)
                if len(parts) == 2:
                    return parts[1].strip()[:60]
        return "Not detected"
    except Exception:
        return "Not detected"


def _detect_shell() -> str:
    return os.environ.get("SHELL", "unknown").rsplit("/", 1)[-1]


def _system_info_lines() -> list[tuple[str, str]]:
    return [
        ("OS", f"{platform.system()} {platform.release()}"),
        ("Distro", platform.freedesktop_os_release().get("PRETTY_NAME", "Unknown") if hasattr(platform, "freedesktop_os_release") else "Unknown"),
        ("Session", _detect_session_type()),
        ("GPU", _detect_gpu()),
        ("Shell", _detect_shell()),
        ("Python", platform.python_version()),
    ]


# ---------------------------------------------------------------------------
# ASCII Art
# ---------------------------------------------------------------------------

LOGO = r"""
[bold cyan]              ___  ___ _ __ ___  ___ _ __          [/]
[bold dodger_blue1]             / __|/ __| '__/ _ \/ _ \ '_ \         [/]
[bold blue]             \__ \ (__| | |  __/  __/ | | |        [/]
[bold medium_purple3]             |___/\___|_|  \___|\___|_| |_|        [/]
[bold bright_cyan]          ____  _ _       _                         [/]
[bold deep_sky_blue1]         |  _ \(_) | ___ | |_                      [/]
[bold steel_blue]         | |_) | | |/ _ \| __|                     [/]
[bold slate_blue1]         |  __/| | | (_) | |_                      [/]
[bold medium_purple1]         |_|   |_|_|\___/ \__|                     [/]
"""

TAGLINE = "[dim italic]Give AI agents eyes and hands on your Linux desktop[/]"

# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------

class WelcomeScreen(Screen):
    """Opening splash with logo and system info."""

    DEFAULT_CSS = """
    WelcomeScreen {
        align: center middle;
    }
    #welcome-box {
        width: 72;
        max-height: 36;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #logo {
        text-align: center;
        margin-bottom: 0;
    }
    #tagline {
        text-align: center;
        margin-bottom: 1;
    }
    #sys-info {
        margin: 1 2;
        padding: 1 2;
        border: round $primary;
        background: $boost;
        height: auto;
    }
    .info-row {
        height: 1;
    }
    .info-label {
        width: 12;
        text-style: bold;
        color: $text;
    }
    .info-value {
        color: $text-muted;
    }
    #welcome-buttons {
        align-horizontal: center;
        margin-top: 1;
        height: 3;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="welcome-box"):
            yield Static(LOGO, id="logo")
            yield Static(TAGLINE, id="tagline")
            yield Rule()
            with Vertical(id="sys-info"):
                yield Static("[bold]System Detection[/]")
                for label, value in _system_info_lines():
                    with Horizontal(classes="info-row"):
                        yield Static(f"  {label}:", classes="info-label")
                        yield Static(value, classes="info-value")
            with Center(id="welcome-buttons"):
                yield Button("Begin Install", variant="success", id="btn-begin")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-begin":
            self.app.push_screen(ComponentScreen())


class ComponentScreen(Screen):
    """Select which components to install."""

    DEFAULT_CSS = """
    ComponentScreen {
        align: center middle;
    }
    #component-box {
        width: 76;
        max-height: 40;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #comp-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }
    .comp-group {
        margin: 0 1;
        padding: 0 1;
        height: auto;
    }
    .comp-help {
        margin-left: 6;
        color: $text-muted;
        margin-bottom: 1;
    }
    #size-info {
        margin: 1 2;
        padding: 1;
        border: round $secondary;
        text-align: center;
        height: auto;
    }
    #comp-buttons {
        align-horizontal: center;
        margin-top: 1;
        height: 3;
    }
    """

    COMPONENTS = [
        ("core", "Core (ydotool, screenshot, uinput)", True, True,
         "Required -- input injection and screen capture"),
        ("omniparser", "OmniParser V2 (UI element detection)", True, False,
         "~1.5 GB weights download. Enables visual UI understanding"),
        ("mcp", "MCP Server (for AI agents)", True, False,
         "Exposes desktop tools via Model Context Protocol"),
        ("systemd", "Systemd service (auto-start)", True, False,
         "Start screen-pilot automatically on login"),
        ("dryrun", "Dry-run mode (log only, no actions)", False, False,
         "Simulate install without making changes"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="component-box"):
            yield Static("[bold cyan]Component Selection[/]", id="comp-title")
            yield Rule()
            with VerticalScroll(classes="comp-group"):
                for cid, label, default, disabled, helptext in self.COMPONENTS:
                    yield Checkbox(label, value=default, id=f"chk-{cid}", disabled=disabled)
                    yield Static(f"  [dim]{helptext}[/]", classes="comp-help")
            yield Static(
                "[bold]Est. download:[/] ~1.8 GB  [bold]Disk:[/] ~3.2 GB (with OmniParser weights)",
                id="size-info",
            )
            with Center(id="comp-buttons"):
                yield Button("\u2190 Back", id="btn-back")
                yield Button("Install \u2192", variant="success", id="btn-install")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-install":
            selected = []
            for cid, *_ in self.COMPONENTS:
                chk = self.query_one(f"#chk-{cid}", Checkbox)
                if chk.value:
                    selected.append(cid)
            self.app.push_screen(ProgressScreen(selected))


class ProgressScreen(Screen):
    """Shows installation progress."""

    DEFAULT_CSS = """
    ProgressScreen {
        align: center middle;
    }
    #progress-box {
        width: 80;
        height: 34;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #prog-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }
    #step-label {
        text-align: center;
        color: $accent;
        margin: 1 0;
    }
    #progress-bar {
        margin: 0 4;
    }
    #install-log {
        border: round $primary;
        margin: 1 1;
        height: 1fr;
        background: $boost;
    }
    #prog-buttons {
        align-horizontal: center;
        height: 3;
    }
    """

    INSTALL_STEPS = [
        ("system_packages", "Installing system packages..."),
        ("uinput_config", "Configuring uinput permissions..."),
        ("conda_env", "Setting up Conda environment..."),
        ("python_packages", "Installing Python packages..."),
        ("omniparser_weights", "Downloading OmniParser weights..."),
        ("systemd_service", "Configuring systemd service..."),
        ("config_file", "Writing configuration file..."),
    ]

    def __init__(self, selected: list[str]) -> None:
        super().__init__()
        self.selected = selected
        self._done = False

    def compose(self) -> ComposeResult:
        with Vertical(id="progress-box"):
            yield Static("[bold green]Installing screen-pilot[/]", id="prog-title")
            yield Rule()
            yield Static("Preparing...", id="step-label")
            yield ProgressBar(total=100, id="progress-bar")
            yield RichLog(id="install-log", highlight=True, markup=True)
            with Center(id="prog-buttons"):
                yield Button("Continue \u2192", variant="success", id="btn-continue", disabled=True)

    def on_mount(self) -> None:
        self._run_install()

    @work(thread=True)
    def _run_install(self) -> None:
        """Simulate the install steps (real logic would go here)."""
        log = self.query_one("#install-log", RichLog)
        bar = self.query_one("#progress-bar", ProgressBar)
        step_label = self.query_one("#step-label", Static)

        dry_run = "dryrun" in self.selected
        steps = list(self.INSTALL_STEPS)

        # Filter steps based on selection
        if "omniparser" not in self.selected:
            steps = [(k, v) for k, v in steps if k != "omniparser_weights"]
        if "systemd" not in self.selected:
            steps = [(k, v) for k, v in steps if k != "systemd_service"]

        total = len(steps)
        per_step = 100 // max(total, 1)

        for i, (step_id, step_text) in enumerate(steps):
            self.call_from_thread(step_label.update, f"[bold]{step_text}[/]")
            self.call_from_thread(log.write, f"[cyan]\u25b6[/] {step_text}")

            if dry_run:
                self.call_from_thread(log.write, "  [yellow][DRY RUN][/] Skipped")
                import time; time.sleep(0.3)
            else:
                # Simulate sub-steps
                import time
                for sub in range(3):
                    substep_msgs = {
                        "system_packages": [
                            "  Checking ydotool...",
                            "  Checking screenshot tools (spectacle/grim/maim)...",
                            "  Verifying uinput kernel module...",
                        ],
                        "uinput_config": [
                            "  Checking /dev/uinput permissions...",
                            "  Verifying udev rules...",
                            "  Testing input injection...",
                        ],
                        "conda_env": [
                            "  Locating conda/mamba...",
                            "  Creating screen-pilot environment...",
                            "  Activating environment...",
                        ],
                        "python_packages": [
                            "  Installing screen-pilot and dependencies...",
                            "  Installing ultralytics for OmniParser...",
                            "  Verifying package integrity...",
                        ],
                        "omniparser_weights": [
                            "  Downloading icon_detect model (1.2 GB)...",
                            "  Downloading icon_caption model (0.3 GB)...",
                            "  Verifying checksums...",
                        ],
                        "systemd_service": [
                            "  Writing screen-pilot.service...",
                            "  Reloading systemd daemon...",
                            "  Enabling service...",
                        ],
                        "config_file": [
                            "  Detecting system configuration...",
                            "  Writing ~/.config/screen-pilot/config.toml...",
                            "  Setting permissions...",
                        ],
                    }
                    msgs = substep_msgs.get(step_id, ["  Processing...", "  Processing...", "  Processing..."])
                    if sub < len(msgs):
                        self.call_from_thread(log.write, f"  [dim]{msgs[sub]}[/]")
                    time.sleep(0.4)

            progress_value = min((i + 1) * per_step, 100)
            self.call_from_thread(bar.update, progress=progress_value)
            self.call_from_thread(log.write, f"  [green]\u2714[/] Done\n")

        self.call_from_thread(bar.update, progress=100)
        self.call_from_thread(step_label.update, "[bold green]Installation complete![/]")
        self.call_from_thread(log.write, "[bold green]\u2728 All components installed successfully![/]")
        self.call_from_thread(self.query_one("#btn-continue", Button).set_class, True, "-active")
        self._done = True
        self.call_from_thread(self._enable_continue)

    def _enable_continue(self) -> None:
        self.query_one("#btn-continue", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-continue" and self._done:
            self.app.push_screen(HealthCheckScreen())


class HealthCheckScreen(Screen):
    """Post-install health check results."""

    DEFAULT_CSS = """
    HealthCheckScreen {
        align: center middle;
    }
    #health-box {
        width: 68;
        max-height: 30;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #health-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }
    .health-row {
        height: 1;
        margin: 0 2;
    }
    .health-name {
        width: 24;
        text-style: bold;
    }
    .health-status {
        width: 30;
    }
    #health-buttons {
        align-horizontal: center;
        margin-top: 1;
        height: 3;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="health-box"):
            yield Static("[bold cyan]Health Check[/]", id="health-title")
            yield Rule()
            checks = self._run_checks()
            for name, status, color in checks:
                with Horizontal(classes="health-row"):
                    yield Static(f"  {name}", classes="health-name")
                    yield Static(f"[{color}]{status}[/]", classes="health-status")
            yield Rule()
            with Center(id="health-buttons"):
                yield Button("Continue \u2192", variant="success", id="btn-register")

    def _run_checks(self) -> list[tuple[str, str, str]]:
        results = []

        # ydotool
        if shutil.which("ydotool"):
            results.append(("ydotool", "\u2714 PASS", "green"))
        else:
            results.append(("ydotool", "\u2718 FAIL - not in PATH", "red"))

        # uinput
        uinput_path = Path("/dev/uinput")
        if uinput_path.exists() and os.access(uinput_path, os.W_OK):
            results.append(("uinput", "\u2714 PASS", "green"))
        elif uinput_path.exists():
            results.append(("uinput", "\u26a0 EXISTS (no write access)", "yellow"))
        else:
            results.append(("uinput", "\u2718 FAIL - /dev/uinput missing", "red"))

        # Screenshot tool
        from screen_pilot.capture import detect_screenshot_tool
        tool = detect_screenshot_tool()
        if tool:
            results.append(("Screenshot", f"\u2714 PASS ({tool})", "green"))
        else:
            results.append(("Screenshot", "\u2718 FAIL - no tool found", "red"))

        # OmniParser weights
        weights_dir = Path("~/.local/share/screen-pilot/weights").expanduser()
        model_file = weights_dir / "icon_detect" / "model.pt"
        if model_file.exists():
            results.append(("OmniParser", "\u2714 PASS (weights found)", "green"))
        else:
            results.append(("OmniParser", "\u26a0 WEIGHTS NOT FOUND", "yellow"))

        # LLM backend
        try:
            from screen_pilot.backend import detect_backend
            backend = detect_backend()
            if backend:
                results.append(("LLM Backend", f"\u2714 DETECTED ({backend.backend}: {backend.model})", "green"))
            else:
                results.append(("LLM Backend", "\u26a0 NOT FOUND", "yellow"))
        except Exception:
            results.append(("LLM Backend", "\u26a0 NOT FOUND", "yellow"))

        return results

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-register":
            self.app.push_screen(RegistrationScreen())


class RegistrationScreen(Screen):
    """Offer to register with detected agent platforms."""

    DEFAULT_CSS = """
    RegistrationScreen {
        align: center middle;
    }
    #register-box {
        width: 72;
        max-height: 28;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #reg-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #reg-desc {
        margin: 0 2 1 2;
        color: $text-muted;
    }
    .reg-group {
        margin: 0 2;
        padding: 0 1;
        height: auto;
    }
    .reg-help {
        margin-left: 6;
        color: $text-muted;
        margin-bottom: 1;
    }
    #reg-buttons {
        align-horizontal: center;
        margin-top: 1;
        height: 3;
    }
    """

    PLATFORMS = [
        ("claude", "Claude Desktop (MCP)", "Register as MCP server in claude_desktop_config.json"),
        ("cursor", "Cursor IDE", "Register as MCP tool provider"),
        ("openinterpreter", "Open Interpreter", "Add screen-pilot tools to Open Interpreter"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="register-box"):
            yield Static("[bold cyan]Agent Platform Registration[/]", id="reg-title")
            yield Rule()
            yield Static(
                "screen-pilot can register itself with AI agent platforms.\n"
                "Select which platforms to configure:",
                id="reg-desc",
            )
            with VerticalScroll(classes="reg-group"):
                for pid, label, helptext in self.PLATFORMS:
                    detected = self._detect_platform(pid)
                    suffix = " [green](detected)[/]" if detected else ""
                    yield Checkbox(f"{label}{suffix}", value=detected, id=f"reg-{pid}")
                    yield Static(f"  [dim]{helptext}[/]", classes="reg-help")
            with Center(id="reg-buttons"):
                yield Button("Skip", id="btn-skip")
                yield Button("Register & Finish", variant="success", id="btn-finish")

    def _detect_platform(self, platform_id: str) -> bool:
        if platform_id == "claude":
            cfg = Path("~/.config/claude/claude_desktop_config.json").expanduser()
            return cfg.parent.exists()
        if platform_id == "cursor":
            return Path("~/.cursor").expanduser().exists()
        return False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("btn-skip", "btn-finish"):
            self.app.push_screen(DoneScreen())


class DoneScreen(Screen):
    """Final screen showing success."""

    DEFAULT_CSS = """
    DoneScreen {
        align: center middle;
    }
    #done-box {
        width: 64;
        max-height: 22;
        border: heavy $success;
        padding: 2 3;
        background: $surface;
    }
    #done-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #done-msg {
        text-align: center;
        margin: 1 0;
        color: $text-muted;
    }
    #done-commands {
        margin: 1 2;
        padding: 1 2;
        border: round $primary;
        background: $boost;
    }
    #done-buttons {
        align-horizontal: center;
        margin-top: 1;
        height: 3;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="done-box"):
            yield Static("[bold green]Installation Complete![/]", id="done-title")
            yield Rule()
            yield Static(
                "screen-pilot is ready. Start using it with these commands:",
                id="done-msg",
            )
            yield Static(
                "[bold]screen-pilot up[/]        Start the service\n"
                "[bold]screen-pilot status[/]    Check status\n"
                "[bold]screen-pilot config[/]    Edit configuration\n"
                "[bold]screen-pilot detect[/]    Detect UI elements\n"
                "[bold]screen-pilot task[/]      Run a desktop task",
                id="done-commands",
            )
            with Center(id="done-buttons"):
                yield Button("Exit", variant="primary", id="btn-exit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-exit":
            self.app.exit()


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------

class InstallerApp(App):
    """screen-pilot interactive installer."""

    TITLE = "screen-pilot installer"
    SUB_TITLE = "v0.1.0"

    CSS = """
    Screen {
        background: $background;
    }
    Button {
        margin: 0 1;
    }
    ProgressBar {
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen(WelcomeScreen())


if __name__ == "__main__":
    InstallerApp().run()

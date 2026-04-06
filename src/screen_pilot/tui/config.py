"""screen-pilot TUI configuration manager -- view and edit settings."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Collapsible,
    Footer,
    Header,
    Input,
    Label,
    Rule,
    Static,
    Switch,
)

from screen_pilot.config import CONFIG_PATH, load_config, save_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _service_status() -> tuple[str, str]:
    """Return (status_text, color) for the systemd user service."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "screen-pilot"],
            capture_output=True, text=True, timeout=5,
        )
        state = result.stdout.strip()
        if state == "active":
            return ("Running", "green")
        if state == "inactive":
            return ("Stopped", "yellow")
        return (state.capitalize(), "red")
    except Exception:
        return ("Unknown", "dim")


def _screenshot_tool() -> str:
    from screen_pilot.capture import detect_screenshot_tool
    tool = detect_screenshot_tool()
    return tool if tool else "none detected"


def _llm_backend_info() -> str:
    try:
        from screen_pilot.backend import detect_backend
        backend = detect_backend()
        if backend:
            return f"{backend.backend} ({backend.model})"
    except Exception:
        pass
    return "not detected"


def _omniparser_status() -> str:
    weights = Path("~/.local/share/screen-pilot/weights/icon_detect/model.pt").expanduser()
    if weights.exists():
        return "Weights present (idle)"
    return "Weights not found"


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class ConfigApp(App):
    """screen-pilot configuration manager."""

    TITLE = "screen-pilot config"
    SUB_TITLE = str(CONFIG_PATH)

    CSS = """
    Screen {
        background: $background;
    }
    #config-scroll {
        margin: 1 2;
    }
    .section-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 0;
    }
    .status-badge {
        margin-left: 2;
    }
    .config-row {
        height: 3;
        margin: 0 1;
        padding: 0 1;
    }
    .config-label {
        width: 22;
        text-style: bold;
        content-align: left middle;
        height: 3;
    }
    .config-input {
        width: 1fr;
        height: 3;
    }
    .config-value {
        width: 1fr;
        content-align: left middle;
        height: 3;
        color: $text-muted;
    }
    .switch-row {
        height: 3;
        margin: 0 1;
        padding: 0 1;
    }
    .switch-label {
        width: 30;
        content-align: left middle;
        height: 3;
    }
    #save-bar {
        align-horizontal: center;
        height: 3;
        dock: bottom;
        margin: 1 0;
    }
    #status-msg {
        text-align: center;
        margin: 1 0;
        height: 1;
    }
    Collapsible {
        margin: 0 0 1 0;
        padding: 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("escape", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        cfg = load_config()

        with VerticalScroll(id="config-scroll"):
            # -- Service Status (read-only) ---
            with Collapsible(title="Service Status", collapsed=False):
                svc_text, svc_color = _service_status()
                with Horizontal(classes="config-row"):
                    yield Static("Systemd service:", classes="config-label")
                    yield Static(f"[{svc_color}]{svc_text}[/]", classes="config-value")
                with Horizontal(classes="config-row"):
                    yield Static("Screenshot tool:", classes="config-label")
                    yield Static(_screenshot_tool(), classes="config-value")
                with Horizontal(classes="config-row"):
                    yield Static("LLM backend:", classes="config-label")
                    yield Static(_llm_backend_info(), classes="config-value")
                with Horizontal(classes="config-row"):
                    yield Static("OmniParser:", classes="config-label")
                    yield Static(_omniparser_status(), classes="config-value")

            # -- Server ---
            with Collapsible(title="Server", collapsed=False):
                with Horizontal(classes="config-row"):
                    yield Static("Host:", classes="config-label")
                    yield Input(value=cfg["server"]["host"], id="cfg-server-host", classes="config-input")
                with Horizontal(classes="config-row"):
                    yield Static("Port:", classes="config-label")
                    yield Input(value=str(cfg["server"]["port"]), id="cfg-server-port", classes="config-input")

            # -- Capture ---
            with Collapsible(title="Capture", collapsed=True):
                with Horizontal(classes="config-row"):
                    yield Static("Tool:", classes="config-label")
                    yield Input(
                        value=cfg["capture"]["tool"],
                        placeholder="auto | spectacle | grim | maim",
                        id="cfg-capture-tool",
                        classes="config-input",
                    )

            # -- Input ---
            with Collapsible(title="Input", collapsed=True):
                with Horizontal(classes="config-row"):
                    yield Static("ydotool socket:", classes="config-label")
                    yield Input(value=cfg["input"]["socket"], id="cfg-input-socket", classes="config-input")

            # -- OmniParser ---
            with Collapsible(title="OmniParser", collapsed=True):
                with Horizontal(classes="config-row"):
                    yield Static("Weights dir:", classes="config-label")
                    yield Input(value=cfg["omniparser"]["weights_dir"], id="cfg-omni-weights", classes="config-input")
                with Horizontal(classes="switch-row"):
                    yield Static("Auto-download weights:", classes="switch-label")
                    yield Switch(value=cfg["omniparser"]["auto_download"], id="cfg-omni-autodownload")
                with Horizontal(classes="config-row"):
                    yield Static("Idle unload (sec):", classes="config-label")
                    yield Input(value=str(cfg["omniparser"]["idle_unload_seconds"]), id="cfg-omni-idle", classes="config-input")
                with Horizontal(classes="config-row"):
                    yield Static("Device:", classes="config-label")
                    yield Input(
                        value=cfg["omniparser"]["device"],
                        placeholder="auto | cpu | cuda",
                        id="cfg-omni-device",
                        classes="config-input",
                    )

            # -- Safety ---
            with Collapsible(title="Safety", collapsed=True):
                with Horizontal(classes="config-row"):
                    yield Static("Max steps/task:", classes="config-label")
                    yield Input(value=str(cfg["safety"]["max_steps_per_task"]), id="cfg-safety-maxsteps", classes="config-input")
                with Horizontal(classes="config-row"):
                    yield Static("Min action delay:", classes="config-label")
                    yield Input(value=str(cfg["safety"]["min_action_delay"]), id="cfg-safety-mindelay", classes="config-input")
                with Horizontal(classes="config-row"):
                    yield Static("Emergency stop:", classes="config-label")
                    yield Input(value=cfg["safety"]["emergency_stop"], id="cfg-safety-estop", classes="config-input")
                with Horizontal(classes="switch-row"):
                    yield Static("Dry-run mode:", classes="switch-label")
                    yield Switch(value=cfg["safety"]["dry_run"], id="cfg-safety-dryrun")
                with Horizontal(classes="config-row"):
                    yield Static("Blocked patterns:", classes="config-label")
                    yield Input(
                        value=", ".join(cfg["safety"]["blocked_patterns"]),
                        id="cfg-safety-patterns",
                        classes="config-input",
                    )

            yield Static("", id="status-msg")

        with Center(id="save-bar"):
            yield Button("Save Config", variant="success", id="btn-save")
            yield Button("Quit", variant="default", id="btn-quit")

        yield Footer()

    def _gather_config(self) -> dict:
        """Read current widget values back into a config dict."""
        cfg = load_config()

        cfg["server"]["host"] = self.query_one("#cfg-server-host", Input).value
        try:
            cfg["server"]["port"] = int(self.query_one("#cfg-server-port", Input).value)
        except ValueError:
            pass

        cfg["capture"]["tool"] = self.query_one("#cfg-capture-tool", Input).value
        cfg["input"]["socket"] = self.query_one("#cfg-input-socket", Input).value

        cfg["omniparser"]["weights_dir"] = self.query_one("#cfg-omni-weights", Input).value
        cfg["omniparser"]["auto_download"] = self.query_one("#cfg-omni-autodownload", Switch).value
        try:
            cfg["omniparser"]["idle_unload_seconds"] = int(self.query_one("#cfg-omni-idle", Input).value)
        except ValueError:
            pass
        cfg["omniparser"]["device"] = self.query_one("#cfg-omni-device", Input).value

        try:
            cfg["safety"]["max_steps_per_task"] = int(self.query_one("#cfg-safety-maxsteps", Input).value)
        except ValueError:
            pass
        try:
            cfg["safety"]["min_action_delay"] = float(self.query_one("#cfg-safety-mindelay", Input).value)
        except ValueError:
            pass
        cfg["safety"]["emergency_stop"] = self.query_one("#cfg-safety-estop", Input).value
        cfg["safety"]["dry_run"] = self.query_one("#cfg-safety-dryrun", Switch).value

        patterns_raw = self.query_one("#cfg-safety-patterns", Input).value
        cfg["safety"]["blocked_patterns"] = [
            p.strip() for p in patterns_raw.split(",") if p.strip()
        ]

        return cfg

    def action_save(self) -> None:
        """Save config triggered by keybinding or button."""
        cfg = self._gather_config()
        save_config(cfg)
        status = self.query_one("#status-msg", Static)
        status.update(f"[bold green]Saved to {CONFIG_PATH}[/]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-quit":
            self.exit()


if __name__ == "__main__":
    ConfigApp().run()

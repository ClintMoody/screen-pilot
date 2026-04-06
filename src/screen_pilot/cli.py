"""screen-pilot CLI - thin HTTP client to the running server."""

import json
import subprocess
import sys

import requests
import typer

from screen_pilot import __version__
from screen_pilot.config import load_config

app = typer.Typer(
    name="screen-pilot",
    help="Give AI agents eyes and hands on your Linux desktop.",
    no_args_is_help=True,
)

config = load_config()
BASE_URL = f"http://{config['server']['host']}:{config['server']['port']}"


def _api(method: str, endpoint: str, **kwargs) -> dict:
    url = f"{BASE_URL}/api/{endpoint}"
    try:
        resp = getattr(requests, method)(url, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        typer.echo("Error: screen-pilot server is not running. Start with: screen-pilot up")
        raise typer.Exit(1)
    except requests.HTTPError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


def version_callback(value: bool):
    if value:
        typer.echo(f"screen-pilot {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True),
):
    pass


@app.command()
def up():
    """Start the screen-pilot service."""
    subprocess.run(["systemctl", "--user", "start", "screen-pilot"], check=False)
    subprocess.run(["systemctl", "--user", "status", "screen-pilot", "--no-pager"], check=False)


@app.command()
def down():
    """Stop the screen-pilot service."""
    subprocess.run(["systemctl", "--user", "stop", "screen-pilot"], check=False)
    typer.echo("screen-pilot stopped.")


@app.command()
def status():
    """Show server status, detected LLM, and loaded models."""
    try:
        data = _api("get", "status")
        typer.echo(f"● screen-pilot running (port {config['server']['port']})")
        typer.echo(f"  Screenshot:  {data.get('screenshot_tool', 'unknown')}")
        typer.echo(f"  OmniParser:  {data.get('omniparser_status', 'unknown')}")
        llm = data.get("llm_backend")
        if llm:
            typer.echo(f"  LLM:         {llm.get('model', '?')} @ {llm.get('backend', '?')}")
        else:
            typer.echo("  LLM:         not detected")
        typer.echo(f"  Safety:      {data.get('safety_summary', 'default')}")
    except typer.Exit:
        pass


@app.command()
def logs(follow: bool = typer.Option(False, "--follow", "-f")):
    """Tail server logs."""
    cmd = ["journalctl", "--user", "-u", "screen-pilot"]
    if follow:
        cmd.append("-f")
    else:
        cmd.extend(["-n", "50"])
    cmd.append("--no-pager")
    subprocess.run(cmd, check=False)


@app.command("screenshot")
def cmd_screenshot(output: str = typer.Option("", "--output", "-o"), json_out: bool = typer.Option(False, "--json")):
    """Capture a screenshot of the entire screen."""
    fmt = "path" if output else "base64"
    result = _api("post", "screenshot", json={"format": fmt})
    if json_out:
        typer.echo(json.dumps(result, indent=2))
    elif output:
        typer.echo(f"Screenshot saved to {result.get('path', output)}")
    else:
        typer.echo(f"Screenshot captured ({len(result.get('base64', ''))} bytes base64)")


@app.command("click")
def cmd_click(
    x: int = typer.Argument(...),
    y: int = typer.Argument(...),
    right: bool = typer.Option(False, "--right"),
    double: bool = typer.Option(False, "--double"),
    mod: str = typer.Option("", "--mod"),
):
    """Click at a screen position."""
    button = "right" if right else "left"
    clicks = 2 if double else 1
    modifiers = [m.strip() for m in mod.split(",") if m.strip()] if mod else None
    result = _api("post", "click", json={"x": x, "y": y, "button": button, "clicks": clicks, "modifiers": modifiers})
    changed = "screen changed" if result.get("screen_changed") else "no change"
    typer.echo(f"Clicked ({x}, {y}) [{button}] -> {changed}")


@app.command("type")
def cmd_type(text: str = typer.Argument(...)):
    """Type text at the current cursor position."""
    _api("post", "type_text", json={"text": text})
    typer.echo(f"Typed: {repr(text)}")


@app.command("key")
def cmd_key(key: str = typer.Argument(...)):
    """Press a key combination (e.g. ctrl+t, super, Return)."""
    _api("post", "press_key", json={"key": key})
    typer.echo(f"Pressed: {key}")


@app.command("scroll")
def cmd_scroll(
    x: int = typer.Argument(...),
    y: int = typer.Argument(...),
    up: bool = typer.Option(False, "--up"),
    amount: int = typer.Option(3, "--amount"),
):
    """Scroll at a screen position."""
    direction = "up" if up else "down"
    _api("post", "scroll", json={"x": x, "y": y, "direction": direction, "amount": amount})
    typer.echo(f"Scrolled {direction} at ({x}, {y})")


@app.command("drag")
def cmd_drag(
    x1: int = typer.Argument(...),
    y1: int = typer.Argument(...),
    x2: int = typer.Argument(...),
    y2: int = typer.Argument(...),
):
    """Drag from one position to another."""
    _api("post", "drag", json={"from_x": x1, "from_y": y1, "to_x": x2, "to_y": y2})
    typer.echo(f"Dragged ({x1},{y1}) -> ({x2},{y2})")


@app.command("hover")
def cmd_hover(x: int = typer.Argument(...), y: int = typer.Argument(...)):
    """Move mouse to a position without clicking."""
    _api("post", "hover", json={"x": x, "y": y})
    typer.echo(f"Hovering at ({x}, {y})")


@app.command("wait")
def cmd_wait(seconds: float = typer.Argument(1.0)):
    """Wait then take a screenshot."""
    _api("post", "wait", json={"seconds": seconds})
    typer.echo(f"Waited {seconds}s, screenshot captured")


@app.command("detect")
def cmd_detect(json_out: bool = typer.Option(False, "--json")):
    """Detect UI elements on screen using OmniParser."""
    result = _api("post", "detect_ui_elements", json={})
    if json_out:
        typer.echo(json.dumps(result, indent=2))
    elif result.get("success"):
        elements = result.get("elements", [])
        typer.echo(f"  #  Class      Position       Size       Conf")
        for i, el in enumerate(elements):
            typer.echo(
                f"  {i:<3}{el['class']:<11}"
                f"({el['center_x']},{el['center_y']})  "
                f"{el['width']}x{el['height']}  "
                f"{el['confidence']:.2f}"
            )
        typer.echo(f"  Found {len(elements)} elements")
    else:
        typer.echo(f"Detection failed: {result.get('error', 'unknown')}")


@app.command("task")
def cmd_task(
    task: str = typer.Argument(...),
    max_steps: int = typer.Option(30, "--max-steps"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """Run an autonomous desktop task."""
    payload = {"task": task, "max_steps": max_steps, "dry_run": dry_run}
    result = _api("post", "desktop_task", json=payload)
    if result.get("success") is False:
        typer.echo(f"Error: {result.get('error')}")
        raise typer.Exit(1)
    typer.echo(f"Task '{task}' -> {result.get('status', '?')} in {result.get('steps_taken', '?')} steps")
    if result.get("reason"):
        typer.echo(f"  Reason: {result['reason']}")


@app.command("detect-backend")
def cmd_detect_backend():
    """Re-probe for local LLM backends."""
    from screen_pilot.backend import detect_backend as _detect
    result = _detect()
    if result:
        typer.echo(f"Detected: {result.backend}")
        typer.echo(f"  Model:  {result.model}")
        typer.echo(f"  URL:    {result.url}")
    else:
        typer.echo("No local LLM backend detected.")


@app.command("install")
def cmd_install():
    """Interactive TUI installer."""
    from screen_pilot.tui.install import InstallerApp
    InstallerApp().run()


@app.command("config")
def cmd_config():
    """TUI configuration manager."""
    from screen_pilot.tui.config import ConfigApp
    ConfigApp().run()


@app.command("uninstall")
def cmd_uninstall():
    """TUI uninstaller."""
    from screen_pilot.tui.uninstall import UninstallApp
    UninstallApp().run()


def main():
    app()


if __name__ == "__main__":
    main()

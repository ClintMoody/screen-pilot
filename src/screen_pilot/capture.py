"""Screenshot capture for Wayland and X11."""

import base64
import glob
import os
import shutil
import subprocess
import time
from pathlib import Path

DEFAULT_SCREENSHOT_PATH = "/tmp/screen-pilot-screenshot.png"
_CLEANUP_INTERVAL = 300  # seconds between cleanup runs
_SCREENSHOT_MAX_AGE = 3600  # delete screenshots older than 1 hour
_last_cleanup = 0.0

TOOL_COMMANDS = {
    "spectacle": ["spectacle", "--background", "--nonotify", "--fullscreen", "--output"],
    "grim": ["grim"],
    "maim": ["maim"],
}

DETECTION_ORDER = ["spectacle", "grim", "maim"]


def detect_screenshot_tool() -> str | None:
    for tool in DETECTION_ORDER:
        if shutil.which(tool):
            return tool
    return None


def capture_screenshot(
    output_path: str = DEFAULT_SCREENSHOT_PATH,
    tool: str = "auto",
    format: str = "path",
) -> dict:
    if tool == "auto":
        tool = detect_screenshot_tool()
    if tool is None:
        return {"success": False, "error": "No screenshot tool found. Install spectacle, grim, or maim."}
    if tool not in TOOL_COMMANDS:
        return {"success": False, "error": f"Unknown screenshot tool: {tool}"}

    cmd = TOOL_COMMANDS[tool] + [output_path]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=10)
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"{tool} failed: {e.stderr.decode()[:200]}"}
    except FileNotFoundError:
        return {"success": False, "error": f"{tool} not found in PATH"}

    result = {"success": True, "path": output_path}
    if format == "base64":
        with open(output_path, "rb") as f:
            result["base64"] = base64.b64encode(f.read()).decode("utf-8")

    _cleanup_old_screenshots()
    return result


def _cleanup_old_screenshots() -> None:
    """Periodically remove old screenshot files from /tmp."""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < _CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    for f in glob.glob("/tmp/sp-*.png"):
        try:
            if now - os.path.getmtime(f) > _SCREENSHOT_MAX_AGE:
                os.unlink(f)
        except OSError:
            pass

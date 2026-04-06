"""screen-pilot MCP server with HTTP API."""

import asyncio
import os
import time

from fastmcp import FastMCP

from screen_pilot.capture import capture_screenshot, DEFAULT_SCREENSHOT_PATH
from screen_pilot.config import load_config
from screen_pilot.detect import OmniParserDetector
from screen_pilot.diff import screenshots_differ
from screen_pilot.input import InputController
from screen_pilot.safety import SafetyEngine
from screen_pilot.backend import detect_backend

from PIL import Image


def _validate_coords(x: int, y: int) -> dict | None:
    """Validate screen coordinates. Returns error dict if invalid, None if OK."""
    if x < 0 or y < 0:
        return {"success": False, "error": f"Coordinates must be non-negative, got ({x}, {y})"}
    return None


def create_mcp_server(config: dict | None = None) -> FastMCP:
    """Create and configure the MCP server with all tools."""

    if config is None:
        config = load_config()

    mcp = FastMCP(
        "screen-pilot",
        instructions=(
            "screen-pilot gives you direct control of the real Linux desktop. "
            "Use these tools to see the screen (screenshot), interact with ANY "
            "application (click, type, press keys, scroll, drag, hover), detect "
            "UI elements via AI vision, and run autonomous desktop tasks. "
            "These tools work with every application on the desktop — browsers "
            "(Brave, Firefox, Chrome, etc.), terminals, file managers, settings, "
            "native apps — without needing any browser engine, Chromium install, "
            "or DOM access. They control the real mouse and keyboard at the OS level. "
            "Prefer these tools over headless browser tools when interacting with "
            "the desktop GUI or any already-open application."
        ),
    )

    input_ctrl = InputController(socket_path=config["input"]["socket"])
    safety = SafetyEngine(config["safety"])
    detector = OmniParserDetector(
        weights_dir=config["omniparser"]["weights_dir"],
        device=config["omniparser"]["device"],
        idle_unload_seconds=config["omniparser"]["idle_unload_seconds"],
    )

    @mcp.tool()
    def screenshot(format: str = "base64") -> dict:
        """Capture the real desktop screen as a PNG image. Works with any application
        visible on screen — browsers (Brave, Firefox, etc.), terminals, file managers,
        settings, dialogs, everything. No browser install required. Use this to see
        what's currently on screen before deciding what action to take. This is a real
        desktop screenshot, not a headless browser render.
        """
        return capture_screenshot(
            output_path=DEFAULT_SCREENSHOT_PATH,
            tool=config["capture"]["tool"],
            format=format,
        )

    @mcp.tool()
    def click(
        x: int, y: int,
        button: str = "left",
        clicks: int = 1,
        modifiers: list[str] | None = None,
    ) -> dict:
        """Click at a real desktop screen position using kernel-level input. Works with
        any visible application — browsers, native apps, system dialogs, desktop icons.
        No Chromium or browser engine needed. Returns whether the screen changed after
        clicking. Supports left/right/middle button, single/double click, and modifier
        keys (ctrl, shift, alt). Use screenshot first to find coordinates.
        """
        err = _validate_coords(x, y)
        if err:
            return err
        action = {"action": "click", "x": x, "y": y}
        check = safety.check_action(action)
        if not check["allowed"]:
            return {"success": False, "error": check["reason"]}

        if safety.is_dry_run:
            return {"success": True, "dry_run": True, "action": f"click ({x},{y})"}

        capture_screenshot(output_path="/tmp/sp-before.png", tool=config["capture"]["tool"])
        before = Image.open("/tmp/sp-before.png")

        result = input_ctrl.click(x, y, button, clicks, modifiers)

        time.sleep(config["safety"]["min_action_delay"])

        capture_screenshot(output_path="/tmp/sp-after.png", tool=config["capture"]["tool"])
        after = Image.open("/tmp/sp-after.png")

        result["screen_changed"] = screenshots_differ(before, after)
        return result

    @mcp.tool()
    def type_text(text: str, modifiers: list[str] | None = None) -> dict:
        """Type text at the current cursor position on the real desktop. Works in any
        focused application — browser URL bars, search fields, terminals, text editors,
        login forms. No browser engine needed. Click a text field first with the click
        tool, then use this to type into it.
        """
        action = {"action": "type_text", "text": text}
        check = safety.check_action(action)
        if not check["allowed"]:
            return {"success": False, "error": check["reason"]}
        if safety.is_dry_run:
            return {"success": True, "dry_run": True, "action": f"type '{text}'"}
        return input_ctrl.type_text(text, modifiers)

    @mcp.tool()
    def press_key(key: str) -> dict:
        """Press a key or key combination on the real desktop. Works globally across
        all applications. Examples: 'super' (open app launcher), 'ctrl+t' (new browser
        tab), 'ctrl+l' (focus URL bar), 'Return' (enter/confirm), 'alt+F4' (close
        window), 'ctrl+c' (copy), 'ctrl+v' (paste). No browser engine needed.
        """
        action = {"action": "press_key", "key": key}
        check = safety.check_action(action)
        if not check["allowed"]:
            return {"success": False, "error": check["reason"]}
        if safety.is_dry_run:
            return {"success": True, "dry_run": True, "action": f"key '{key}'"}
        return input_ctrl.press_key(key)

    @mcp.tool()
    def scroll(x: int, y: int, direction: str = "down", amount: int = 3) -> dict:
        """Scroll at a real desktop screen position. Works in any application — browser
        pages, file lists, settings panels, documents. No browser engine needed.
        """
        err = _validate_coords(x, y)
        if err:
            return err
        action = {"action": "scroll", "x": x, "y": y}
        check = safety.check_action(action)
        if not check["allowed"]:
            return {"success": False, "error": check["reason"]}
        if safety.is_dry_run:
            return {"success": True, "dry_run": True, "action": f"scroll {direction} at ({x},{y})"}
        return input_ctrl.scroll(x, y, direction, amount)

    @mcp.tool()
    def drag(from_x: int, from_y: int, to_x: int, to_y: int, button: str = "left") -> dict:
        """Drag from one desktop position to another. For drag-and-drop, window resizing,
        slider adjustment, text selection. Works with any application. No browser needed.
        """
        err = _validate_coords(from_x, from_y)
        if err:
            return err
        err = _validate_coords(to_x, to_y)
        if err:
            return err
        action = {"action": "drag", "from_x": from_x, "from_y": from_y}
        check = safety.check_action(action)
        if not check["allowed"]:
            return {"success": False, "error": check["reason"]}
        if safety.is_dry_run:
            return {"success": True, "dry_run": True, "action": f"drag ({from_x},{from_y})->({to_x},{to_y})"}
        return input_ctrl.drag(from_x, from_y, to_x, to_y, button)

    @mcp.tool()
    def hover(x: int, y: int) -> dict:
        """Move mouse to a real desktop position without clicking. Triggers tooltips,
        dropdown menus, and hover states in any application. No browser engine needed.
        """
        err = _validate_coords(x, y)
        if err:
            return err
        action = {"action": "hover", "x": x, "y": y}
        check = safety.check_action(action)
        if not check["allowed"]:
            return {"success": False, "error": check["reason"]}
        if safety.is_dry_run:
            return {"success": True, "dry_run": True, "action": f"hover ({x},{y})"}
        return input_ctrl.hover(x, y)

    @mcp.tool()
    async def wait(seconds: float = 1.0) -> dict:
        """Wait for the specified duration, then capture a real desktop screenshot.
        Use after actions that trigger animations, page loads, dialog popups, or
        application startup. Returns the screenshot so you can see the result.
        """
        if seconds < 0:
            return {"success": False, "error": "Wait seconds must be non-negative"}
        if seconds > 60:
            seconds = 60
        await asyncio.sleep(seconds)
        return capture_screenshot(
            output_path=DEFAULT_SCREENSHOT_PATH,
            tool=config["capture"]["tool"],
            format="base64",
        )

    @mcp.tool()
    def detect_ui_elements(screenshot_path: str = "") -> dict:
        """Detect interactive UI elements (buttons, icons, fields) on the real desktop
        screen using AI vision (OmniParser). Returns element positions, sizes, and
        types so you know where to click. Works with any application visible on screen.
        No browser engine or DOM access needed — this uses computer vision on the
        actual pixels. Requires the vision extra: pip install screen-pilot[vision]
        """
        if not screenshot_path:
            capture_screenshot(
                output_path=DEFAULT_SCREENSHOT_PATH,
                tool=config["capture"]["tool"],
            )
            screenshot_path = DEFAULT_SCREENSHOT_PATH
        try:
            elements = detector.detect(screenshot_path)
            return {"success": True, "elements": elements, "count": len(elements)}
        except ImportError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Detection failed: {e}"}

    @mcp.tool()
    def desktop_task(task: str, max_steps: int = 30, dry_run: bool = False) -> dict:
        """Run an autonomous visual task on the real desktop. Give a natural language
        instruction and the agent loop will repeatedly screenshot the real screen,
        detect UI elements via AI vision, reason about the next action, and execute
        it (click, type, key press) until the task is complete. Works with any
        application — browsers, native apps, system settings, file managers.

        No browser engine or Chromium install needed. This controls the actual desktop
        the same way a human would: by looking at the screen and using the mouse/keyboard.

        Requires a local LLM backend (auto-detected: llama.cpp, Ollama, LM Studio, vLLM).
        If no backend is available, use the low-level tools (screenshot, click, type_text,
        press_key, etc.) and handle the reasoning yourself.

        Examples:
          desktop_task("Open the browser and navigate to github.com")
          desktop_task("Find the settings app and enable dark mode")
          desktop_task("Open a terminal and run htop")
        """
        backend = detect_backend(
            override_url=config["backend"].get("url"),
            override_model=config["backend"].get("model"),
        )
        if backend is None:
            return {
                "success": False,
                "error": (
                    "No local LLM backend detected. desktop_task requires a running "
                    "LLM server (llama.cpp, Ollama, LM Studio, or vLLM). "
                    "Use the low-level tools (screenshot, click, type_text, "
                    "detect_ui_elements, etc.) and handle reasoning yourself."
                ),
            }

        from screen_pilot.loop import run_task_loop
        return run_task_loop(
            task=task,
            max_steps=max_steps,
            dry_run=dry_run or safety.is_dry_run,
            backend=backend,
            input_ctrl=input_ctrl,
            detector=detector,
            safety=safety,
            capture_config=config["capture"],
        )

    return mcp


def create_http_app(config: dict | None = None):
    """Create FastAPI app wrapping MCP tools as HTTP endpoints, with MCP mounted."""
    from fastapi import FastAPI

    if config is None:
        config = load_config()

    # Create MCP server with streamable-http transport
    mcp = create_mcp_server(config)
    mcp_http_app = mcp.http_app(path="/", transport="streamable-http")

    # FastAPI must use the MCP app's lifespan for session management
    http_app = FastAPI(title="screen-pilot", version="0.1.0", lifespan=mcp_http_app.lifespan)
    http_app.mount("/mcp", mcp_http_app)

    input_ctrl = InputController(socket_path=config["input"]["socket"])
    safety = SafetyEngine(config["safety"])
    detector = OmniParserDetector(
        weights_dir=config["omniparser"]["weights_dir"],
        device=config["omniparser"]["device"],
        idle_unload_seconds=config["omniparser"]["idle_unload_seconds"],
    )

    @http_app.post("/api/screenshot")
    async def api_screenshot(body: dict = {}):
        return capture_screenshot(
            tool=config["capture"]["tool"],
            format=body.get("format", "base64"),
        )

    @http_app.post("/api/click")
    async def api_click(body: dict):
        x, y = body.get("x", 0), body.get("y", 0)
        err = _validate_coords(x, y)
        if err:
            return err
        action = {"action": "click", "x": x, "y": y}
        check = safety.check_action(action)
        if not check["allowed"]:
            return {"success": False, "error": check["reason"]}
        if safety.is_dry_run:
            return {"success": True, "dry_run": True}

        capture_screenshot(output_path="/tmp/sp-before.png", tool=config["capture"]["tool"])
        before = Image.open("/tmp/sp-before.png")

        result = input_ctrl.click(x, y, body.get("button", "left"), body.get("clicks", 1), body.get("modifiers"))

        time.sleep(config["safety"]["min_action_delay"])

        capture_screenshot(output_path="/tmp/sp-after.png", tool=config["capture"]["tool"])
        after = Image.open("/tmp/sp-after.png")
        result["screen_changed"] = screenshots_differ(before, after)
        return result

    @http_app.post("/api/type_text")
    async def api_type_text(body: dict):
        action = {"action": "type_text", "text": body.get("text", "")}
        check = safety.check_action(action)
        if not check["allowed"]:
            return {"success": False, "error": check["reason"]}
        return input_ctrl.type_text(body.get("text", ""), body.get("modifiers"))

    @http_app.post("/api/press_key")
    async def api_press_key(body: dict):
        return input_ctrl.press_key(body.get("key", ""))

    @http_app.post("/api/scroll")
    async def api_scroll(body: dict):
        return input_ctrl.scroll(
            body.get("x", 0), body.get("y", 0),
            body.get("direction", "down"), body.get("amount", 3),
        )

    @http_app.post("/api/drag")
    async def api_drag(body: dict):
        return input_ctrl.drag(
            body.get("from_x", 0), body.get("from_y", 0),
            body.get("to_x", 0), body.get("to_y", 0),
            body.get("button", "left"),
        )

    @http_app.post("/api/hover")
    async def api_hover(body: dict):
        return input_ctrl.hover(body.get("x", 0), body.get("y", 0))

    @http_app.post("/api/wait")
    async def api_wait(body: dict = {}):
        seconds = max(0, min(body.get("seconds", 1.0), 60))
        await asyncio.sleep(seconds)
        return capture_screenshot(tool=config["capture"]["tool"], format="base64")

    @http_app.post("/api/detect_ui_elements")
    async def api_detect(body: dict = {}):
        path = body.get("screenshot_path", "")
        if not path:
            capture_screenshot(output_path=DEFAULT_SCREENSHOT_PATH, tool=config["capture"]["tool"])
            path = DEFAULT_SCREENSHOT_PATH
        try:
            elements = detector.detect(path)
            return {"success": True, "elements": elements, "count": len(elements)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @http_app.post("/api/desktop_task")
    async def api_desktop_task(body: dict):
        backend = detect_backend(
            override_url=config["backend"].get("url"),
            override_model=config["backend"].get("model"),
        )
        if backend is None:
            return {"success": False, "error": "No local LLM backend detected."}
        from screen_pilot.loop import run_task_loop
        return run_task_loop(
            task=body.get("task", ""),
            max_steps=body.get("max_steps", 30),
            dry_run=body.get("dry_run", False) or safety.is_dry_run,
            backend=backend,
            input_ctrl=input_ctrl,
            detector=detector,
            safety=safety,
            capture_config=config["capture"],
        )

    @http_app.get("/api/status")
    async def api_status():
        backend = detect_backend(
            override_url=config["backend"].get("url"),
            override_model=config["backend"].get("model"),
        )
        return {
            "running": True,
            "port": config["server"]["port"],
            "screenshot_tool": config["capture"]["tool"],
            "omniparser_status": "loaded" if detector.is_loaded else "idle",
            "llm_backend": {
                "backend": backend.backend, "model": backend.model, "url": backend.url
            } if backend else None,
            "safety_summary": f"{len(config['safety']['blocked_patterns'])} blocked patterns",
        }

    @http_app.get("/api/health")
    async def api_health():
        return {"status": "ok"}

    return http_app


def main():
    """Entry point for screen-pilot-server."""
    import sys
    import uvicorn

    config = load_config()

    if "--mcp" in sys.argv:
        mcp = create_mcp_server(config)
        mcp.run(transport="stdio")
    else:
        http_app = create_http_app(config)
        uvicorn.run(
            http_app,
            host=config["server"]["host"],
            port=config["server"]["port"],
        )


if __name__ == "__main__":
    main()

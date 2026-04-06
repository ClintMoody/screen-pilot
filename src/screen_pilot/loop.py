"""Autonomous desktop task loop with action history and verification."""

import time
from PIL import Image

from screen_pilot.backend import LLMBackend
from screen_pilot.capture import capture_screenshot, DEFAULT_SCREENSHOT_PATH
from screen_pilot.diff import screenshots_differ
from screen_pilot.input import InputController
from screen_pilot.detect import OmniParserDetector
from screen_pilot.safety import SafetyEngine


def _build_prompt(
    task: str,
    elements: list[dict],
    screen_size: tuple[int, int],
    history: list[dict],
    step: int,
    max_steps: int,
) -> str:
    w, h = screen_size
    parts = [
        f"You are a computer control agent on a Linux desktop (KDE Plasma, Wayland).",
        f"You can control the mouse and keyboard. This is step {step}/{max_steps}.",
        f"",
        f"YOUR TASK: {task}",
        f"",
        f"SCREEN: {w}x{h}",
    ]

    if elements:
        parts.append(f"\nDetected {len(elements)} UI elements:")
        for i, el in enumerate(elements[:30]):
            parts.append(
                f"  [{i}] type={el['class']} center=({el['center_x']},{el['center_y']}) "
                f"size={el['width']}x{el['height']} conf={el['confidence']:.2f}"
            )
    else:
        parts.append("\nNo UI elements detected on screen.")

    if history:
        parts.append(f"\nACTION HISTORY (last {len(history)} steps):")
        for h_entry in history[-10:]:
            changed = "screen changed" if h_entry.get("screen_changed") else "no change"
            parts.append(f"  Step {h_entry['step']}: {h_entry['action']} -> {changed}")

    parts.append(
        "\nReply with ONLY a JSON object:\n"
        '{"action": "click"|"type"|"key"|"scroll"|"done"|"fail", '
        '"x": <int>, "y": <int>, "text": "<string>", "key": "<key>", '
        '"reason": "<brief why>"}'
    )

    return "\n".join(parts)


def _execute_action(action: dict, input_ctrl: InputController) -> dict:
    action_type = action.get("action", "")

    if action_type == "click":
        x, y = action.get("x"), action.get("y")
        if x is None or y is None:
            return {"success": False, "error": "LLM response missing 'x' or 'y' for click action"}
        return input_ctrl.click(int(x), int(y))
    elif action_type == "type":
        text = action.get("text", "")
        if not text:
            return {"success": False, "error": "LLM response missing 'text' for type action"}
        return input_ctrl.type_text(text)
    elif action_type == "key":
        key = action.get("key", "")
        if not key:
            return {"success": False, "error": "LLM response missing 'key' for key action"}
        return input_ctrl.press_key(key)
    elif action_type == "scroll":
        direction = action.get("text", action.get("direction", "down"))
        return input_ctrl.scroll(action.get("x", 0), action.get("y", 0), direction)
    elif action_type == "done":
        return {"success": True, "done": True}
    elif action_type == "fail":
        return {"success": False, "done": True, "reason": action.get("reason", "")}

    return {"success": False, "error": f"Unknown action: {action_type}"}


def run_task_loop(
    task: str,
    max_steps: int,
    dry_run: bool,
    backend: LLMBackend,
    input_ctrl: InputController,
    detector: OmniParserDetector,
    safety: SafetyEngine,
    capture_config: dict,
) -> dict:
    history: list[dict] = []
    steps_log: list[dict] = []

    for step in range(1, max_steps + 1):
        step_check = safety.check_step(step)
        if not step_check["allowed"]:
            return {"status": "stopped", "reason": step_check["reason"], "steps_taken": step - 1, "log": steps_log}

        cap_result = capture_screenshot(output_path=DEFAULT_SCREENSHOT_PATH, tool=capture_config.get("tool", "auto"))
        if not cap_result.get("success", False):
            return {"status": "error", "reason": f"Screenshot failed: {cap_result.get('error')}", "steps_taken": step - 1, "log": steps_log}

        img = Image.open(DEFAULT_SCREENSHOT_PATH)
        screen_size = img.size

        try:
            elements = detector.detect(DEFAULT_SCREENSHOT_PATH)
        except Exception:
            elements = []

        prompt = _build_prompt(task, elements, screen_size, history, step, max_steps)
        action = backend.chat(prompt)

        step_entry = {"step": step, "elements_found": len(elements), "llm_action": action}

        safety_check = safety.check_action(action)
        if not safety_check["allowed"]:
            step_entry["blocked"] = safety_check["reason"]
            steps_log.append(step_entry)
            continue

        action_desc = f"{action.get('action', '?')} {action.get('key', action.get('text', ''))}"
        if action.get("x"):
            action_desc += f" at ({action['x']},{action['y']})"

        if dry_run:
            step_entry["dry_run"] = action_desc
            steps_log.append(step_entry)
            if action.get("action") in ("done", "fail"):
                return {"status": action["action"], "reason": action.get("reason", ""), "steps_taken": step, "log": steps_log}
            history.append({"step": step, "action": action_desc, "screen_changed": None})
            continue

        result = _execute_action(action, input_ctrl)
        step_entry["result"] = result

        if result.get("done"):
            steps_log.append(step_entry)
            status = "done" if result.get("success") else "fail"
            return {"status": status, "reason": action.get("reason", ""), "steps_taken": step, "log": steps_log}

        time.sleep(safety.min_delay)
        capture_screenshot(output_path="/tmp/sp-verify.png", tool=capture_config.get("tool", "auto"))
        after = Image.open("/tmp/sp-verify.png")
        screen_changed = screenshots_differ(img, after)
        step_entry["screen_changed"] = screen_changed

        history.append({"step": step, "action": action_desc, "screen_changed": screen_changed})
        steps_log.append(step_entry)

    return {"status": "max_steps_reached", "steps_taken": max_steps, "log": steps_log}

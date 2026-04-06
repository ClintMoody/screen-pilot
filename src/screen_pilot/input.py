"""Input control via ydotool (uinput-based, works on Wayland and X11)."""

import os
import subprocess
import time

BUTTON_MAP = {"left": "0x40", "right": "0x41", "middle": "0x42"}


class InputController:
    def __init__(self, socket_path: str = "/run/user/1000/.ydotool_socket"):
        self.socket_path = socket_path

    def _run_ydotool(self, args: list[str]) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["YDOTOOL_SOCKET"] = self.socket_path
        return subprocess.run(
            ["ydotool"] + args,
            env=env,
            capture_output=True,
            timeout=5,
        )

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1, modifiers: list[str] | None = None) -> dict:
        try:
            self._run_ydotool(["mousemove", "--absolute", "-x", str(x), "-y", str(y)])
            time.sleep(0.05)
            btn_code = BUTTON_MAP.get(button, "0x40")
            for _ in range(clicks):
                self._run_ydotool(["click", btn_code])
                time.sleep(0.05)
            return {"success": True, "action": "click", "x": x, "y": y, "button": button}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def type_text(self, text: str, modifiers: list[str] | None = None) -> dict:
        try:
            self._run_ydotool(["type", text])
            return {"success": True, "action": "type_text", "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def press_key(self, key: str) -> dict:
        try:
            self._run_ydotool(["key", key])
            return {"success": True, "action": "press_key", "key": key}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def scroll(self, x: int, y: int, direction: str = "down", amount: int = 3) -> dict:
        try:
            self._run_ydotool(["mousemove", "--absolute", "-x", str(x), "-y", str(y)])
            time.sleep(0.05)
            wheel_delta = str(amount) if direction == "down" else str(-amount)
            self._run_ydotool(["mousemove", "--wheel", "--", "0", wheel_delta])
            return {"success": True, "action": "scroll", "direction": direction}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int, button: str = "left") -> dict:
        try:
            self._run_ydotool(["mousemove", "--absolute", "-x", str(from_x), "-y", str(from_y)])
            time.sleep(0.05)
            btn_code = BUTTON_MAP.get(button, "0x40")
            self._run_ydotool(["click", "--button", btn_code, "--next-delay", "0"])
            time.sleep(0.05)
            self._run_ydotool(["mousemove", "--absolute", "-x", str(to_x), "-y", str(to_y)])
            time.sleep(0.05)
            self._run_ydotool(["click", btn_code])
            return {"success": True, "action": "drag", "from": [from_x, from_y], "to": [to_x, to_y]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def hover(self, x: int, y: int) -> dict:
        try:
            self._run_ydotool(["mousemove", "--absolute", "-x", str(x), "-y", str(y)])
            return {"success": True, "action": "hover", "x": x, "y": y}
        except Exception as e:
            return {"success": False, "error": str(e)}

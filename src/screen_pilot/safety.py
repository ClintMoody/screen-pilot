"""Safety guardrails for screen-pilot actions."""


class SafetyEngine:
    def __init__(self, config: dict):
        self.max_steps = config.get("max_steps_per_task", 30)
        self.min_delay = config.get("min_action_delay", 0.5)
        self.blocked_patterns = config.get("blocked_patterns", [])
        self.blocked_regions = config.get("blocked_regions", [])
        self.allowed_apps = config.get("allowed_apps", [])
        self.is_dry_run = config.get("dry_run", False)

    def check_action(self, action: dict) -> dict:
        action_type = action.get("action", "")

        if action_type == "type_text":
            text = action.get("text", "").lower()
            for pattern in self.blocked_patterns:
                if pattern.lower() in text:
                    return {"allowed": False, "reason": f"Blocked pattern detected: '{pattern}'"}

        if action_type in ("click", "drag", "hover", "scroll"):
            x = action.get("x", action.get("from_x", 0))
            y = action.get("y", action.get("from_y", 0))
            for region in self.blocked_regions:
                rx, ry = region["x"], region["y"]
                rw, rh = region["w"], region["h"]
                label = region.get("label", "unnamed region")
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    return {"allowed": False, "reason": f"Action blocked: click falls within protected region '{label}'"}

        return {"allowed": True}

    def check_step(self, step_number: int) -> dict:
        if step_number > self.max_steps:
            return {"allowed": False, "reason": f"Max steps ({self.max_steps}) exceeded"}
        return {"allowed": True}

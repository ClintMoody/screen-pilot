from screen_pilot.safety import SafetyEngine


def _default_safety_config():
    return {
        "max_steps_per_task": 30,
        "min_action_delay": 0.5,
        "confirm_actions": [],
        "emergency_stop": "ctrl+shift+escape",
        "dry_run": False,
        "blocked_regions": [],
        "blocked_patterns": ["sudo rm -rf", ":(){ :|:&", "dd if="],
        "allowed_apps": [],
    }


def test_allows_safe_click():
    engine = SafetyEngine(_default_safety_config())
    result = engine.check_action({"action": "click", "x": 500, "y": 300})
    assert result["allowed"] is True

def test_blocks_dangerous_text():
    engine = SafetyEngine(_default_safety_config())
    result = engine.check_action({"action": "type_text", "text": "sudo rm -rf /"})
    assert result["allowed"] is False
    assert "blocked pattern" in result["reason"].lower()

def test_blocks_fork_bomb():
    engine = SafetyEngine(_default_safety_config())
    result = engine.check_action({"action": "type_text", "text": ":(){ :|:& };:"})
    assert result["allowed"] is False

def test_blocks_click_in_blocked_region():
    config = _default_safety_config()
    config["blocked_regions"] = [{"x": 1700, "y": 0, "w": 220, "h": 50, "label": "system tray"}]
    engine = SafetyEngine(config)
    result = engine.check_action({"action": "click", "x": 1800, "y": 25})
    assert result["allowed"] is False
    assert "system tray" in result["reason"]

def test_allows_click_outside_blocked_region():
    config = _default_safety_config()
    config["blocked_regions"] = [{"x": 1700, "y": 0, "w": 220, "h": 50, "label": "system tray"}]
    engine = SafetyEngine(config)
    result = engine.check_action({"action": "click", "x": 500, "y": 300})
    assert result["allowed"] is True

def test_step_counter():
    engine = SafetyEngine(_default_safety_config())
    for i in range(30):
        result = engine.check_step(i + 1)
        assert result["allowed"] is True
    result = engine.check_step(31)
    assert result["allowed"] is False

def test_dry_run_mode():
    config = _default_safety_config()
    config["dry_run"] = True
    engine = SafetyEngine(config)
    assert engine.is_dry_run is True

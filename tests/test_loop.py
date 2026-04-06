from unittest.mock import patch, MagicMock

from screen_pilot.loop import run_task_loop, _build_prompt
from screen_pilot.safety import SafetyEngine
from screen_pilot.backend import LLMBackend


def test_build_prompt_includes_task():
    prompt = _build_prompt(
        task="Open Firefox",
        elements=[],
        screen_size=(1920, 1080),
        history=[],
        step=1,
        max_steps=10,
    )
    assert "Open Firefox" in prompt
    assert "1920x1080" in prompt


def test_build_prompt_includes_history():
    history = [{"step": 1, "action": "key super", "screen_changed": True}]
    prompt = _build_prompt(
        task="test",
        elements=[],
        screen_size=(1920, 1080),
        history=history,
        step=2,
        max_steps=10,
    )
    assert "key super" in prompt


def test_loop_dry_run():
    backend = LLMBackend("test", "http://fake", "model")
    input_ctrl = MagicMock()
    safety = SafetyEngine({
        "max_steps_per_task": 5,
        "min_action_delay": 0,
        "blocked_patterns": [],
        "blocked_regions": [],
        "allowed_apps": [],
        "dry_run": False,
    })
    detector = MagicMock()
    detector.detect.return_value = []

    with patch("screen_pilot.loop.capture_screenshot") as mock_cap, \
         patch("screen_pilot.loop.Image") as mock_img:
        mock_cap.return_value = {"success": True, "path": "/tmp/test.png"}
        mock_img.open.return_value = MagicMock(size=(1920, 1080))
        backend.chat = MagicMock(return_value={"action": "done", "reason": "test"})

        result = run_task_loop(
            task="test task",
            max_steps=5,
            dry_run=True,
            backend=backend,
            input_ctrl=input_ctrl,
            detector=detector,
            safety=safety,
            capture_config={"tool": "auto"},
        )

    assert result["status"] == "done"

from unittest.mock import patch, MagicMock
from screen_pilot.input import InputController


def test_click_basic():
    ctrl = InputController(socket_path="/tmp/fake.sock")
    with patch.object(ctrl, "_run_ydotool") as mock:
        result = ctrl.click(500, 300)
        assert result["success"] is True
        assert mock.call_count == 2

def test_type_text():
    ctrl = InputController(socket_path="/tmp/fake.sock")
    with patch.object(ctrl, "_run_ydotool") as mock:
        result = ctrl.type_text("hello world")
        assert result["success"] is True
        mock.assert_called_once()

def test_press_key():
    ctrl = InputController(socket_path="/tmp/fake.sock")
    with patch.object(ctrl, "_run_ydotool") as mock:
        result = ctrl.press_key("ctrl+t")
        assert result["success"] is True

def test_drag():
    ctrl = InputController(socket_path="/tmp/fake.sock")
    with patch.object(ctrl, "_run_ydotool") as mock:
        result = ctrl.drag(100, 100, 500, 500)
        assert result["success"] is True

def test_hover():
    ctrl = InputController(socket_path="/tmp/fake.sock")
    with patch.object(ctrl, "_run_ydotool") as mock:
        result = ctrl.hover(960, 540)
        assert result["success"] is True

def test_scroll():
    ctrl = InputController(socket_path="/tmp/fake.sock")
    with patch.object(ctrl, "_run_ydotool") as mock:
        result = ctrl.scroll(500, 300, "down", 3)
        assert result["success"] is True

from unittest.mock import patch, MagicMock

from screen_pilot.capture import detect_screenshot_tool, capture_screenshot


def test_detect_screenshot_tool_spectacle():
    with patch("shutil.which", side_effect=lambda x: "/usr/bin/spectacle" if x == "spectacle" else None):
        assert detect_screenshot_tool() == "spectacle"


def test_detect_screenshot_tool_grim():
    with patch("shutil.which", side_effect=lambda x: "/usr/bin/grim" if x == "grim" else None):
        assert detect_screenshot_tool() == "grim"


def test_detect_screenshot_tool_maim():
    with patch("shutil.which", side_effect=lambda x: "/usr/bin/maim" if x == "maim" else None):
        assert detect_screenshot_tool() == "maim"


def test_detect_screenshot_tool_none():
    with patch("shutil.which", return_value=None):
        assert detect_screenshot_tool() is None


def test_capture_screenshot_spectacle(tmp_path):
    output = tmp_path / "test.png"
    with patch("screen_pilot.capture.detect_screenshot_tool", return_value="spectacle"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        output.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        result = capture_screenshot(str(output), tool="spectacle")
        assert result["success"] is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "spectacle" in cmd

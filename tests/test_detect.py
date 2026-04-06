from unittest.mock import patch, MagicMock
from screen_pilot.detect import OmniParserDetector


def test_detector_starts_unloaded():
    detector = OmniParserDetector(weights_dir="/fake/path", device="cpu")
    assert detector.is_loaded is False


def test_detector_detect_returns_elements():
    detector = OmniParserDetector(weights_dir="/fake/path", device="cpu")

    mock_box = MagicMock()
    mock_box.xyxy = [MagicMock()]
    mock_box.xyxy[0].tolist.return_value = [100.0, 200.0, 150.0, 250.0]
    mock_box.conf.item.return_value = 0.92
    mock_box.cls = MagicMock()
    mock_box.cls.item.return_value = 0

    mock_result = MagicMock()
    mock_result.boxes = [mock_box]
    mock_result.names = {0: "icon"}

    mock_model = MagicMock()
    mock_model.return_value = [mock_result]

    with patch("screen_pilot.detect.YOLO", return_value=mock_model):
        detector.load()
        elements = detector.detect("/tmp/test.png")

    assert len(elements) == 1
    assert elements[0]["class"] == "icon"
    assert elements[0]["center_x"] == 125
    assert elements[0]["center_y"] == 225
    assert elements[0]["confidence"] == 0.92


def test_detector_unload():
    detector = OmniParserDetector(weights_dir="/fake/path", device="cpu")
    with patch("screen_pilot.detect.YOLO", return_value=MagicMock()):
        detector.load()
        assert detector.is_loaded is True
        detector.unload()
        assert detector.is_loaded is False

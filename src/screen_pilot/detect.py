"""OmniParser V2 UI element detection with lazy loading and idle unload."""

import threading
import time
from pathlib import Path

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


class OmniParserDetector:
    def __init__(
        self,
        weights_dir: str = "~/.local/share/screen-pilot/weights",
        device: str = "auto",
        idle_unload_seconds: int = 60,
    ):
        self.weights_dir = Path(weights_dir).expanduser()
        self.model_path = self.weights_dir / "icon_detect" / "model.pt"
        self.device = device
        self.idle_unload_seconds = idle_unload_seconds
        self._model = None
        self._last_use: float = 0
        self._unload_timer: threading.Timer | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self._model is not None:
            return
        if YOLO is None:
            raise ImportError(
                "OmniParser requires ultralytics. Install with: "
                "pip install screen-pilot[vision]"
            )
        self._model = YOLO(str(self.model_path))
        self._last_use = time.time()
        self._schedule_unload()

    def unload(self) -> None:
        if self._unload_timer:
            self._unload_timer.cancel()
            self._unload_timer = None
        self._model = None

    def _schedule_unload(self) -> None:
        if self._unload_timer:
            self._unload_timer.cancel()
        self._unload_timer = threading.Timer(
            self.idle_unload_seconds, self._idle_unload
        )
        self._unload_timer.daemon = True
        self._unload_timer.start()

    def _idle_unload(self) -> None:
        if time.time() - self._last_use >= self.idle_unload_seconds:
            self.unload()

    def detect(self, screenshot_path: str) -> list[dict]:
        if not self.is_loaded:
            self.load()
        self._last_use = time.time()
        self._schedule_unload()

        results = self._model(screenshot_path)

        elements = []
        for r in results:
            names = r.names if hasattr(r, "names") else {}
            for box in r.boxes:
                bbox = box.xyxy[0].tolist()
                conf = box.conf.item()
                cls_id = int(box.cls.item()) if box.cls is not None else -1
                cls_name = names.get(cls_id, "unknown")
                elements.append({
                    "class": cls_name,
                    "center_x": int((bbox[0] + bbox[2]) / 2),
                    "center_y": int((bbox[1] + bbox[3]) / 2),
                    "width": int(bbox[2] - bbox[0]),
                    "height": int(bbox[3] - bbox[1]),
                    "confidence": round(conf, 3),
                    "bbox": bbox,
                })

        elements.sort(key=lambda e: (e["center_y"], e["center_x"]))
        return elements

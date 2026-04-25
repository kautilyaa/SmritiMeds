"""YOLO-based pill detection helpers for SmritiMeds."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_WEIGHTS_PATH = "models/medical-pills-yolo.pt"


class DetectorUnavailableError(RuntimeError):
    """Raised when local YOLO detection cannot run."""


def _load_ultralytics() -> Any:
    try:
        from ultralytics import YOLO
    except Exception as exc:  # pragma: no cover - depends on optional local env
        raise DetectorUnavailableError(
            "YOLO detection requires optional local vision dependencies. "
            "Install requirements-local-vision.txt in a Python 3.12 environment."
        ) from exc
    return YOLO


@lru_cache(maxsize=1)
def load_detector() -> Any:
    YOLO = _load_ultralytics()
    weights_path = Path(os.getenv("SMRITIMEDS_YOLO_WEIGHTS", DEFAULT_WEIGHTS_PATH))
    if not weights_path.is_absolute():
        weights_path = Path(__file__).resolve().parent / weights_path
    if not weights_path.exists():
        raise DetectorUnavailableError(
            f"YOLO weights not found at {weights_path}. "
            "Train them with scripts/train_yolo_medical_pills.py or notebook 03 first."
        )
    return YOLO(str(weights_path))


def detect_pills(image: Any, conf: float = 0.25, iou: float = 0.45) -> list[dict[str, Any]]:
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise DetectorUnavailableError("Pillow is required for image detection.") from exc

    model = load_detector()
    if not isinstance(image, Image.Image):
        image = Image.open(image)
    image = image.convert("RGB")

    result = model.predict(image, conf=conf, iou=iou, verbose=False)[0]
    boxes = result.boxes
    if boxes is None:
        return []

    detections: list[dict[str, Any]] = []
    for index, xyxy in enumerate(boxes.xyxy.cpu().tolist()):
        x1, y1, x2, y2 = [int(value) for value in xyxy]
        crop = image.crop((x1, y1, x2, y2))
        score = float(boxes.conf[index].item()) if boxes.conf is not None else None
        class_id = int(boxes.cls[index].item()) if boxes.cls is not None else 0
        detections.append(
            {
                "box": [x1, y1, x2, y2],
                "confidence": score,
                "class_id": class_id,
                "crop": crop,
            }
        )
    return detections


def annotate_detections(image: Any, detections: list[dict[str, Any]]) -> Any:
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:  # pragma: no cover
        raise DetectorUnavailableError("Pillow is required for annotation rendering.") from exc

    if not isinstance(image, Image.Image):
        image = Image.open(image)
    annotated = image.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)

    for index, detection in enumerate(detections, start=1):
        x1, y1, x2, y2 = detection["box"]
        confidence = detection.get("confidence")
        color = "#5B8CFF"
        draw.rectangle((x1, y1, x2, y2), outline=color, width=4)
        label = f"Pill {index}"
        if confidence is not None:
            label = f"{label} {confidence:.2f}"
        draw.text((x1 + 6, max(6, y1 - 18)), label, fill=color)

    return annotated

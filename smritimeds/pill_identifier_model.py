"""Local Hugging Face pill classification support for SmritiMeds."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests


MODEL_ID = "pillIdentifierAI/pillIdentifier"
ENCODER_URL = "https://huggingface.co/spaces/pillIdentifierAI/pill_identifier/resolve/main/encoder.npy"


class LocalVisionUnavailableError(RuntimeError):
    """Raised when local vision dependencies or weights are unavailable."""


def _cache_dir() -> Path:
    return Path(__file__).resolve().parent.parent / ".cache" / "pill_identifier"


def _local_model_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "models" / "pillIdentifierAI-pillIdentifier"


def _ensure_encoder_file() -> Path:
    cache_dir = _cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    encoder_path = cache_dir / "encoder.npy"
    if encoder_path.exists():
        return encoder_path

    response = requests.get(ENCODER_URL, timeout=60)
    response.raise_for_status()
    encoder_path.write_bytes(response.content)
    return encoder_path


def _load_dependencies() -> tuple[Any, Any, Any, Any]:
    try:
        import numpy as np
        import torch
        from PIL import Image
        from transformers import AutoImageProcessor, ViTForImageClassification, ViTImageProcessor
    except Exception as exc:  # pragma: no cover - depends on optional local env
        raise LocalVisionUnavailableError(
            "Local Hugging Face pill identification requires optional dependencies. "
            "Install requirements-local-vision.txt in a Python 3.12 environment."
        ) from exc

    return np, torch, Image, (AutoImageProcessor, ViTForImageClassification, ViTImageProcessor)


@lru_cache(maxsize=1)
def load_pill_identifier() -> tuple[Any, Any, Any]:
    np, _torch, _Image, transformers = _load_dependencies()
    AutoImageProcessor, ViTForImageClassification, ViTImageProcessor = transformers

    encoder_path = _ensure_encoder_file()
    classes = np.load(encoder_path, allow_pickle=True)
    model_source = _local_model_dir() if _local_model_dir().exists() else MODEL_ID
    try:
        processor = AutoImageProcessor.from_pretrained(model_source)
    except OSError:
        processor = ViTImageProcessor(
            size={"height": 224, "width": 224},
            do_resize=True,
            do_normalize=True,
            do_rescale=False,
            image_mean=[0.5, 0.5, 0.5],
            image_std=[0.5, 0.5, 0.5],
        )
    try:
        model = ViTForImageClassification.from_pretrained(model_source)
    except RuntimeError as exc:
        raise LocalVisionUnavailableError(
            "The published pillIdentifierAI/pillIdentifier checkpoint has inconsistent classifier metadata "
            "versus weights in the downloaded files. The assets are cached locally, but classification "
            "cannot be loaded reliably without a corrected checkpoint."
        ) from exc
    model.eval()
    return processor, model, classes


def predict_pill_candidates(image: Any, top_k: int = 5) -> list[dict[str, Any]]:
    _, torch, Image, _transformers = _load_dependencies()
    processor, model, classes = load_pill_identifier()

    if not isinstance(image, Image.Image):
        image = Image.open(image)
    image = image.convert("RGB")

    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        probabilities = torch.softmax(outputs.logits, dim=-1)[0]

    count = min(top_k, probabilities.shape[0])
    scores, indices = torch.topk(probabilities, k=count)

    predictions: list[dict[str, Any]] = []
    for score, index in zip(scores.tolist(), indices.tolist(), strict=False):
        label = str(classes[index]) if index < len(classes) else f"LABEL_{index}"
        predictions.append(
            {
                "label": label,
                "score": float(score),
            }
        )

    return predictions


def local_model_status() -> dict[str, Any]:
    return {
        "model_id": MODEL_ID,
        "local_model_cached": _local_model_dir().exists(),
        "encoder_cached": (_cache_dir() / "encoder.npy").exists(),
        "yolo_weights": os.getenv("SMRITIMEDS_YOLO_WEIGHTS", "SmritiMeds/models/medical-pills-yolo.pt"),
    }

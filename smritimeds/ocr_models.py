"""OCR model adapters for printed and handwritten medical documents."""

from __future__ import annotations

import importlib.util
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


MEDOCR_MODEL_ID = "naazimsnh02/medocr-vision"
HANDWRITTEN_MODEL_ID = "chinmays18/medical-prescription-ocr"


class OCRUnavailableError(RuntimeError):
    """Raised when an OCR backend cannot be loaded locally."""


def _local_dir(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / "models" / name


def _normalize_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def backend_status() -> dict[str, dict[str, Any]]:
    return {
        "medocr_vision": {
            "model_id": MEDOCR_MODEL_ID,
            "package_ready": importlib.util.find_spec("unsloth") is not None,
            "local_model_cached": _local_dir("naazimsnh02-medocr-vision").exists(),
            "notes": "Requires unsloth + trust_remote_code; recommended for printed medical documents and forms.",
        },
        "handwritten_donut": {
            "model_id": HANDWRITTEN_MODEL_ID,
            "package_ready": importlib.util.find_spec("transformers") is not None,
            "local_model_cached": _local_dir("chinmays18-medical-prescription-ocr").exists(),
            "notes": "Transformers-based Donut OCR for handwritten prescriptions.",
        },
    }


@lru_cache(maxsize=1)
def _load_medocr_components() -> tuple[Any, Any, Any]:
    try:
        from PIL import Image
        from transformers import AutoProcessor
        from unsloth import FastVisionModel
    except Exception as exc:  # pragma: no cover - optional environment
        raise OCRUnavailableError(
            "medocr-vision requires `unsloth`, `transformers`, and its trust_remote_code stack. "
            "Install the OCR extras in a compatible environment before using this backend."
        ) from exc

    model_source = _local_dir("naazimsnh02-medocr-vision")
    source = str(model_source) if model_source.exists() else MEDOCR_MODEL_ID
    model, tokenizer = FastVisionModel.from_pretrained(source)
    processor = AutoProcessor.from_pretrained(source, trust_remote_code=True)
    FastVisionModel.for_inference(model)
    return model, tokenizer, processor


def extract_text_with_medocr(image: Any) -> dict[str, Any]:
    try:
        import torch
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise OCRUnavailableError("Pillow and torch are required for medocr-vision.") from exc

    model, tokenizer, processor = _load_medocr_components()
    if not isinstance(image, Image.Image):
        image = Image.open(image)
    image = image.convert("RGB")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": "Extract all text from this medical document:"},
            ],
        }
    ]
    text_prompt = processor.tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    inputs = processor(
        image,
        text_prompt,
        add_special_tokens=False,
        return_tensors="pt",
    ).to(device)
    model.to(device)

    output = model.generate(
        **inputs,
        max_new_tokens=256,
        use_cache=False,
        temperature=1.5,
        min_p=0.1,
    )
    text = tokenizer.decode(output[0], skip_special_tokens=True)
    return {
        "backend": "medocr-vision",
        "raw_text": _normalize_text(text),
    }


@lru_cache(maxsize=1)
def _load_handwritten_components() -> tuple[Any, Any]:
    try:
        from transformers import DonutProcessor, VisionEncoderDecoderModel
    except Exception as exc:  # pragma: no cover
        raise OCRUnavailableError(
            "Handwritten OCR requires transformers with Donut support."
        ) from exc

    model_source = _local_dir("chinmays18-medical-prescription-ocr")
    source = str(model_source) if model_source.exists() else HANDWRITTEN_MODEL_ID
    processor = DonutProcessor.from_pretrained(source)
    model = VisionEncoderDecoderModel.from_pretrained(source)
    return processor, model


def extract_text_with_handwritten_ocr(image: Any) -> dict[str, Any]:
    try:
        import torch
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise OCRUnavailableError("Pillow and torch are required for handwritten OCR.") from exc

    processor, model = _load_handwritten_components()
    if not isinstance(image, Image.Image):
        image = Image.open(image)
    image = image.convert("RGB")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)
    decoder_input_ids = processor.tokenizer("<s_ocr>", return_tensors="pt").input_ids.to(device)

    generated_ids = model.generate(
        pixel_values,
        decoder_input_ids=decoder_input_ids,
        max_length=512,
        num_beams=1,
        early_stopping=True,
    )
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return {
        "backend": "medical-prescription-ocr",
        "raw_text": _normalize_text(text),
    }


def route_ocr_document(image: Any, mode: str) -> dict[str, Any]:
    if mode == "printed_document":
        return extract_text_with_medocr(image)
    if mode == "handwritten_prescription":
        return extract_text_with_handwritten_ocr(image)

    errors: list[str] = []
    for extractor in (extract_text_with_medocr, extract_text_with_handwritten_ocr):
        try:
            result = extractor(image)
            if len(result.get("raw_text", "")) >= 12:
                result["mode"] = "auto"
                return result
        except OCRUnavailableError as exc:
            errors.append(str(exc))
        except Exception as exc:  # pragma: no cover - backend resilience
            errors.append(f"{extractor.__name__}: {exc}")

    raise OCRUnavailableError("No OCR backend produced usable output. " + " | ".join(errors))

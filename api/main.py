"""SmritiMeds API service."""

from __future__ import annotations

import io
import re
from collections import Counter
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image

from smritimeds.anthropic_client import SmritiMedsAPIError, analyze_extracted_text, analyze_medication_images
from smritimeds.config import load_config, load_env_file
from smritimeds.local_pill_pipeline import analyze_local_pills
from smritimeds.ocr_models import OCRUnavailableError, backend_status, route_ocr_document
from smritimeds.pill_identifier_model import local_model_status


load_env_file()
app = FastAPI(title="SmritiMeds API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_upload(upload: UploadFile | None) -> tuple[bytes, str] | None:
    if upload is None:
        return None
    content = upload.file.read()
    if not content:
        return None
    return content, upload.content_type or "image/jpeg"


def _image_from_bytes(payload: tuple[bytes, str] | None) -> Image.Image | None:
    if payload is None:
        return None
    return Image.open(io.BytesIO(payload[0])).convert("RGB")


def _fallback_ocr_analysis(raw_text: str) -> dict[str, Any]:
    preview = raw_text[:300].strip()
    return {
        "medication_name": None,
        "strength": None,
        "instructions_raw": preview or None,
        "times_per_day": 0,
        "schedule": [],
        "pill_appearance": {
            "color": None,
            "shape": None,
            "imprint": None,
            "notes": "No visual pill analysis was run in OCR-only fallback mode.",
        },
        "verification_summary": "OCR text extracted, but schedule generation is unavailable without Anthropic.",
        "confidence_notes": ["Manual review required.", "Schedule could not be normalized automatically."],
        "needs_manual_review": True,
    }


def _ocr_text_looks_usable(raw_text: str) -> bool:
    text = (raw_text or "").strip()
    if len(text) < 20:
        return False

    if re.search(r"([A-Za-z]{2,6})\1{5,}", text):
        return False

    tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
    if len(tokens) < 4:
        return False

    counts = Counter(tokens)
    _, most_common_count = counts.most_common(1)[0]
    if most_common_count >= max(10, len(tokens) // 3):
        return False

    medical_hints = {"mg", "tablet", "capsule", "take", "daily", "before", "after", "doctor", "patient"}
    if not any(token in medical_hints for token in tokens) and not any(char.isdigit() for char in text):
        return False

    return True


def _claude_image_fallback(
    config: Any,
    *,
    label_payload: tuple[bytes, str],
    verification_payload: tuple[bytes, str] | None = None,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    try:
        analysis, raw_output = analyze_medication_images(
            config,
            label_image_bytes=label_payload[0],
            label_mime_type=label_payload[1],
            verification_image_bytes=verification_payload[0] if verification_payload else None,
            verification_mime_type=verification_payload[1] if verification_payload else None,
        )
        return analysis, raw_output, None
    except SmritiMedsAPIError as exc:
        return None, None, str(exc)


@app.get("/api/health")
def health() -> dict[str, Any]:
    config = load_config()
    return {
        "ok": True,
        "anthropic_configured": bool(config.api_key),
        "anthropic_model": config.model,
        "ocr_backends": backend_status(),
        "local_vision": local_model_status(),
    }


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "service": "SmritiMeds API",
            "message": "API is running. Open the web application at http://127.0.0.1:5173 or call /api/health.",
            "web_url": "http://127.0.0.1:5173",
            "health_url": "/api/health",
            "analyze_url": "/api/analyze",
        }
    )


@app.get("/favicon.ico")
def favicon() -> JSONResponse:
    return JSONResponse({}, status_code=204)


@app.post("/api/analyze")
def analyze(
    mode: str = Form("auto"),
    run_local_vision: bool = Form(False),
    label_image: UploadFile = File(...),
    verification_image: UploadFile | None = File(None),
) -> dict[str, Any]:
    config = load_config()
    label_payload = _read_upload(label_image)
    verification_payload = _read_upload(verification_image)
    if label_payload is None:
        return {"ok": False, "error": "Missing label_image payload."}

    effective_mode = mode
    if mode == "auto":
        effective_mode = "printed_document" if verification_payload is None else "bottle_label"

    response: dict[str, Any] = {
        "ok": True,
        "mode": effective_mode,
        "ocr": None,
        "analysis": None,
        "raw_model_output": None,
        "local_vision": None,
    }

    if effective_mode in {"printed_document", "handwritten_prescription"}:
        source_image = _image_from_bytes(label_payload)
        try:
            ocr_result = route_ocr_document(source_image, effective_mode)
            response["ocr"] = ocr_result
        except OCRUnavailableError as exc:
            response["ocr"] = {
                "backend": effective_mode,
                "raw_text": "",
                "error": str(exc),
            }
            ocr_result = None

        if ocr_result and _ocr_text_looks_usable(ocr_result.get("raw_text", "")):
            try:
                analysis, raw_output = analyze_extracted_text(
                    config,
                    raw_text=ocr_result["raw_text"],
                    document_kind=effective_mode,
                )
            except SmritiMedsAPIError:
                analysis = _fallback_ocr_analysis(ocr_result["raw_text"])
                raw_output = None
            response["analysis"] = analysis
            response["raw_model_output"] = raw_output
        else:
            fallback_analysis, fallback_raw, fallback_error = _claude_image_fallback(
                config,
                label_payload=label_payload,
                verification_payload=verification_payload,
            )
            if fallback_analysis is not None:
                response["analysis"] = fallback_analysis
                response["raw_model_output"] = fallback_raw
                response["ocr"] = {
                    **(response["ocr"] or {}),
                    "fallback": "claude_vision",
                    "fallback_reason": (
                        (response["ocr"] or {}).get("error")
                        or "OCR backend produced low-quality or unusable text."
                    ),
                }
            else:
                response["analysis"] = _fallback_ocr_analysis("")
                if fallback_error:
                    response["ocr"] = {
                        **(response["ocr"] or {}),
                        "fallback": "claude_vision_failed",
                        "fallback_reason": fallback_error,
                    }

    else:
        try:
            analysis, raw_output = analyze_medication_images(
                config,
                label_image_bytes=label_payload[0],
                label_mime_type=label_payload[1],
                verification_image_bytes=verification_payload[0] if verification_payload else None,
                verification_mime_type=verification_payload[1] if verification_payload else None,
            )
            response["analysis"] = analysis
            response["raw_model_output"] = raw_output
        except SmritiMedsAPIError as exc:
            response["ok"] = False
            response["error"] = str(exc)
            return response

    if run_local_vision:
        try:
            local_image = _image_from_bytes(verification_payload or label_payload)
            if local_image is not None:
                local_result = analyze_local_pills(
                    local_image,
                    medication_name=(response["analysis"] or {}).get("medication_name"),
                )
                response["local_vision"] = {
                    "count": local_result["count"],
                    "detections": [
                        {
                            "pill_index": item["pill_index"],
                            "box": item["box"],
                            "confidence": item["confidence"],
                            "best_match": item["best_match"],
                            "predictions": item["predictions"],
                        }
                        for item in local_result["detections"]
                    ],
                    "classifier_warning": local_result.get("classifier_warning"),
                    "assessment": local_result.get("assessment"),
                }
        except Exception as exc:  # pragma: no cover - resilience path
            response["local_vision"] = {"error": str(exc)}

    return response

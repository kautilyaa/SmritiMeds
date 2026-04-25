"""Hybrid YOLO + Hugging Face local pill analysis for SmritiMeds."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from pill_detector import annotate_detections, detect_pills
from pill_identifier_model import LocalVisionUnavailableError, predict_pill_candidates


def _match_score(medication_name: str | None, candidate_label: str) -> float:
    if not medication_name:
        return 0.0
    medication_name = medication_name.lower().strip()
    candidate_label = candidate_label.lower().strip()
    if not medication_name or not candidate_label:
        return 0.0
    if medication_name in candidate_label or candidate_label in medication_name:
        return 1.0
    return SequenceMatcher(None, medication_name, candidate_label).ratio()


def analyze_local_pills(
    image: Any,
    *,
    medication_name: str | None = None,
    top_k: int = 3,
) -> dict[str, Any]:
    detections = detect_pills(image)
    annotated = annotate_detections(image, detections)

    detection_results: list[dict[str, Any]] = []
    classifier_warning: str | None = None
    for index, detection in enumerate(detections, start=1):
        try:
            predictions = predict_pill_candidates(detection["crop"], top_k=top_k)
        except LocalVisionUnavailableError as exc:
            predictions = []
            classifier_warning = str(exc)
        best_match = None
        if medication_name and predictions:
            best_match = max(
                (
                    {
                        **prediction,
                        "match_score": _match_score(medication_name, prediction["label"]),
                    }
                    for prediction in predictions
                ),
                key=lambda item: item["match_score"],
            )

        detection_results.append(
            {
                "pill_index": index,
                "box": detection["box"],
                "confidence": detection.get("confidence"),
                "crop": detection["crop"],
                "predictions": predictions,
                "best_match": best_match,
            }
        )

    return {
        "count": len(detection_results),
        "annotated_image": annotated,
        "detections": detection_results,
        "classifier_warning": classifier_warning,
    }

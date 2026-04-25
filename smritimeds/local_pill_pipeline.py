"""Hybrid YOLO + Hugging Face local pill analysis for SmritiMeds."""

from __future__ import annotations

from difflib import SequenceMatcher
from statistics import mean
from typing import Any

from .pill_detector import annotate_detections, detect_pills
from .pill_identifier_model import LocalVisionUnavailableError, predict_pill_candidates


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


def _build_visual_only_assessment(
    detections: list[dict[str, Any]],
    *,
    classifier_warning: str | None,
    medication_name: str | None,
) -> dict[str, Any]:
    risk_factors = [
        "Visual surface inspection cannot confirm chemical authenticity.",
        "Counterfeit tablets can imitate color, shape, and imprint cues.",
    ]
    penalty = 0.35

    if not detections:
        penalty += 0.25
        risk_factors.append("No pill region was detected, so visual verification is weak.")
    else:
        detection_confidences = [
            detection.get("confidence", 0.0) or 0.0
            for detection in detections
        ]
        best_match_scores = [
            (detection.get("best_match") or {}).get("match_score", 0.0) or 0.0
            for detection in detections
        ]
        top_prediction_scores = [
            (detection.get("predictions") or [{}])[0].get("score", 0.0)
            if detection.get("predictions")
            else 0.0
            for detection in detections
        ]

        mean_detection_confidence = mean(detection_confidences)
        mean_match_score = mean(best_match_scores) if any(best_match_scores) else 0.0
        mean_prediction_score = mean(top_prediction_scores) if any(top_prediction_scores) else 0.0

        if mean_detection_confidence < 0.7:
            penalty += 0.12
            risk_factors.append("Detection confidence is modest, which weakens trust in the visual crop.")
        if mean_prediction_score < 0.75:
            penalty += 0.1
            risk_factors.append("Classifier confidence is limited, suggesting visual ambiguity.")
        if medication_name and mean_match_score < 0.7:
            penalty += 0.1
            risk_factors.append("The best visual match is not strongly aligned with the extracted medication name.")

    if classifier_warning:
        penalty += 0.15
        risk_factors.append("Local classifier reliability is reduced because the published checkpoint is inconsistent.")

    penalty = max(0.0, min(round(penalty, 2), 0.95))

    return {
        "authentication_scope": "visual_surface_only",
        "chemical_authentication_available": False,
        "visual_only_confidence_penalty": penalty,
        "adjusted_visual_confidence": round(max(0.0, 1.0 - penalty), 2),
        "safety_summary": (
            "This local vision result is a structural surface check only. "
            "It should be treated as supportive evidence, not as proof of tablet authenticity."
        ),
        "paper_basis": (
            "Inspired by the PillSure dual-modal premise that visual analysis alone is insufficient "
            "without an independent chemical signal."
        ),
        "risk_factors": risk_factors,
    }


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
        "assessment": _build_visual_only_assessment(
            detection_results,
            classifier_warning=classifier_warning,
            medication_name=medication_name,
        ),
    }

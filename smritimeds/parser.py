"""JSON extraction and normalization helpers for SmritiMeds."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


class ParseError(ValueError):
    """Raised when the model output cannot be parsed safely."""


TIME_OF_DAY_ORDER = ["Morning", "Noon", "Evening", "Bedtime", "Custom"]


@dataclass(frozen=True)
class ReminderEntry:
    time_of_day: str
    label: str
    dose: str | None
    items: list[str]
    notes: str | None


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        parts = stripped.splitlines()
        if len(parts) >= 3:
            return "\n".join(parts[1:-1]).strip()
    return stripped


def _extract_json_object(text: str) -> str:
    cleaned = _strip_code_fences(text)
    start = cleaned.find("{")
    if start == -1:
        raise ParseError("No JSON object found in model output")

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start : index + 1]

    raise ParseError("Incomplete JSON object in model output")


def _coerce_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value).strip() or None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def _coerce_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return max(0, int(value))
    text = str(value).strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else 0


def _normalize_schedule(raw_schedule: Any, medication_name: str | None) -> list[dict[str, Any]]:
    if not isinstance(raw_schedule, list):
        return []

    normalized: list[dict[str, Any]] = []
    for raw_entry in raw_schedule:
        if not isinstance(raw_entry, dict):
            continue
        time_of_day = _coerce_string(raw_entry.get("time_of_day")) or "Custom"
        if time_of_day not in TIME_OF_DAY_ORDER:
            time_of_day = "Custom"

        label = _coerce_string(raw_entry.get("label")) or f"{time_of_day} reminder"
        dose = _coerce_string(raw_entry.get("dose"))

        raw_items = raw_entry.get("items")
        if isinstance(raw_items, list):
            items = [item for item in (_coerce_string(value) for value in raw_items) if item]
        else:
            items = []
        if not items and medication_name:
            items = [medication_name]

        normalized.append(
            {
                "time_of_day": time_of_day,
                "label": label,
                "dose": dose,
                "items": items,
                "notes": _coerce_string(raw_entry.get("notes")),
            }
        )

    normalized.sort(key=lambda entry: TIME_OF_DAY_ORDER.index(entry["time_of_day"]))
    return normalized


def parse_model_output(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(_extract_json_object(text))
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON returned by model: {exc}") from exc

    if not isinstance(payload, dict):
        raise ParseError("Expected top-level JSON object")

    medication_name = _coerce_string(payload.get("medication_name"))
    confidence_notes = payload.get("confidence_notes")
    if not isinstance(confidence_notes, list):
        confidence_notes = []

    normalized = {
        "medication_name": medication_name,
        "strength": _coerce_string(payload.get("strength")),
        "instructions_raw": _coerce_string(payload.get("instructions_raw")),
        "times_per_day": _coerce_int(payload.get("times_per_day")),
        "schedule": _normalize_schedule(payload.get("schedule"), medication_name),
        "pill_appearance": {
            "color": _coerce_string((payload.get("pill_appearance") or {}).get("color"))
            if isinstance(payload.get("pill_appearance"), dict)
            else None,
            "shape": _coerce_string((payload.get("pill_appearance") or {}).get("shape"))
            if isinstance(payload.get("pill_appearance"), dict)
            else None,
            "imprint": _coerce_string((payload.get("pill_appearance") or {}).get("imprint"))
            if isinstance(payload.get("pill_appearance"), dict)
            else None,
            "notes": _coerce_string((payload.get("pill_appearance") or {}).get("notes"))
            if isinstance(payload.get("pill_appearance"), dict)
            else None,
        },
        "verification_summary": _coerce_string(payload.get("verification_summary"))
        or "Verification result unavailable.",
        "confidence_notes": [
            note for note in (_coerce_string(value) for value in confidence_notes) if note
        ],
        "needs_manual_review": _coerce_bool(payload.get("needs_manual_review")),
    }

    return normalized

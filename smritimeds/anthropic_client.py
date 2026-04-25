"""Thin Anthropic Messages API client for image-based SmritiMeds analysis."""

from __future__ import annotations

import base64
from dataclasses import asdict
from typing import Any

import requests

from .config import AppConfig
from .parser import ParseError, parse_model_output
from .prompting import SYSTEM_PROMPT, build_text_analysis_prompt, build_user_prompt


class SmritiMedsAPIError(RuntimeError):
    """Raised for transport or provider-level failures."""


def _encode_image(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _image_block(image_bytes: bytes, mime_type: str) -> dict[str, Any]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": mime_type,
            "data": _encode_image(image_bytes),
        },
    }


def _text_from_response(payload: dict[str, Any]) -> str:
    texts: list[str] = []
    for block in payload.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
            texts.append(block["text"])
    return "\n".join(texts).strip()


def _messages_request(config: AppConfig, body: dict[str, Any]) -> str:
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=body,
        timeout=config.timeout_seconds,
    )
    if response.status_code >= 400:
        raise SmritiMedsAPIError(
            f"Anthropic request failed ({response.status_code}): {response.text[:500]}"
        )
    return _text_from_response(response.json())


def analyze_medication_images(
    config: AppConfig,
    *,
    label_image_bytes: bytes,
    label_mime_type: str,
    verification_image_bytes: bytes | None = None,
    verification_mime_type: str | None = None,
) -> tuple[dict[str, Any], str]:
    if not config.api_key:
        raise SmritiMedsAPIError("Missing ANTHROPIC_API_KEY")

    content: list[dict[str, Any]] = [
        _image_block(label_image_bytes, label_mime_type),
        {"type": "text", "text": build_user_prompt(include_verification_image=verification_image_bytes is not None)},
    ]

    if verification_image_bytes and verification_mime_type:
        content.insert(1, _image_block(verification_image_bytes, verification_mime_type))

    body = {
        "model": config.model,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": content}],
    }

    last_error: Exception | None = None
    for attempt in range(2):
        raw_text = _messages_request(config, body)
        try:
            return parse_model_output(raw_text), raw_text
        except ParseError as exc:
            last_error = exc
            body["messages"][0]["content"][-1]["text"] = (
                build_user_prompt(include_verification_image=verification_image_bytes is not None)
                + "\n\nIMPORTANT: Your previous response was not valid JSON. Return a single valid JSON object only."
            )

    raise SmritiMedsAPIError(f"Model returned unusable JSON after retry: {last_error}")


def analyze_extracted_text(
    config: AppConfig,
    *,
    raw_text: str,
    document_kind: str,
) -> tuple[dict[str, Any], str]:
    if not config.api_key:
        raise SmritiMedsAPIError("Missing ANTHROPIC_API_KEY")

    body = {
        "model": config.model,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": build_text_analysis_prompt(raw_text=raw_text, document_kind=document_kind),
            }
        ],
    }

    last_error: Exception | None = None
    for _attempt in range(2):
        raw_response = _messages_request(config, body)
        try:
            return parse_model_output(raw_response), raw_response
        except ParseError as exc:
            last_error = exc
            body["messages"][0]["content"] = (
                build_text_analysis_prompt(raw_text=raw_text, document_kind=document_kind)
                + "\n\nIMPORTANT: Return valid JSON only."
            )

    raise SmritiMedsAPIError(f"Model returned unusable JSON after retry: {last_error}")


def debug_request_summary(config: AppConfig) -> dict[str, Any]:
    safe = asdict(config)
    safe["api_key"] = "set" if config.api_key else "missing"
    return safe

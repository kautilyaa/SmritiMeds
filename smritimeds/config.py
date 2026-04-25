"""Environment-backed configuration for the SmritiMeds application."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MODEL = "claude-sonnet-4-20250514"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class AppConfig:
    api_key: str | None
    model: str = DEFAULT_MODEL
    max_tokens: int = 1400
    temperature: float = 0.1
    timeout_seconds: int = 90


def load_env_file(path: str | os.PathLike[str] = ".env", override: bool = False) -> bool:
    env_path = Path(path)
    candidate_paths = []
    if env_path.is_absolute():
        candidate_paths.append(env_path)
    else:
        candidate_paths.extend(
            [
                Path.cwd() / env_path,
                PROJECT_ROOT / env_path,
            ]
        )

    resolved_path = next((candidate for candidate in candidate_paths if candidate.exists()), None)
    if resolved_path is None:
        return False
    for raw_line in resolved_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = value
    return True


def load_config() -> AppConfig:
    return AppConfig(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model=os.getenv("SMRITIMEDS_MODEL", os.getenv("PILLBOX_MODEL", DEFAULT_MODEL)),
        max_tokens=int(os.getenv("SMRITIMEDS_MAX_TOKENS", os.getenv("PILLBOX_MAX_TOKENS", "1400"))),
        temperature=float(os.getenv("SMRITIMEDS_TEMPERATURE", os.getenv("PILLBOX_TEMPERATURE", "0.1"))),
        timeout_seconds=int(
            os.getenv("SMRITIMEDS_TIMEOUT_SECONDS", os.getenv("PILLBOX_TIMEOUT_SECONDS", "90"))
        ),
    )

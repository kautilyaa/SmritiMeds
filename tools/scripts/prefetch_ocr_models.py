"""Prefetch OCR models into the local SmritiMeds models directory."""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-medocr",
        action="store_true",
        help="Also download the larger medocr-vision checkpoint.",
    )
    return parser.parse_args()


def download(repo_id: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(target),
        local_dir_use_symlinks=False,
    )
    print(f"Downloaded {repo_id} -> {target}")


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[2]
    download(
        "chinmays18/medical-prescription-ocr",
        root / "models" / "chinmays18-medical-prescription-ocr",
    )
    if args.include_medocr:
        download(
            "naazimsnh02/medocr-vision",
            root / "models" / "naazimsnh02-medocr-vision",
        )


if __name__ == "__main__":
    main()

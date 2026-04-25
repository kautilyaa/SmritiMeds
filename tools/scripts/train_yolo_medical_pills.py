"""Quick training script for a lightweight medical pill detector."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=5, help="Short lightweight training run.")
    parser.add_argument("--imgsz", type=int, default=416, help="Smaller image size for faster training.")
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="cpu", help="Set to cuda, mps, or cpu.")
    parser.add_argument("--model", default="models/yolo11n.pt", help="Base YOLO checkpoint.")
    parser.add_argument(
        "--dataset-dir",
        default="data/Ultralytics-Medical-pills",
        help="Local dataset cache directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from huggingface_hub import snapshot_download
    from ultralytics import YOLO

    project_root = Path(__file__).resolve().parents[2]
    dataset_dir = project_root / args.dataset_dir
    dataset_dir.parent.mkdir(parents=True, exist_ok=True)

    local_dataset = snapshot_download(
        repo_id="Ultralytics/Medical-pills",
        repo_type="dataset",
        local_dir=str(dataset_dir),
        local_dir_use_symlinks=False,
    )
    dataset_yaml = Path(local_dataset) / "medical-pills.yaml"
    if not dataset_yaml.exists():
        raise FileNotFoundError(f"Dataset YAML not found at {dataset_yaml}")

    model_path = Path(args.model)
    if not model_path.is_absolute():
        model_path = project_root / model_path
    model = YOLO(str(model_path) if model_path.exists() else args.model)
    run = model.train(
        data=str(dataset_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        cache=True,
        workers=2,
        project=str(project_root / "models"),
        name="medical-pills-yolo",
        exist_ok=True,
    )

    weights_dir = Path(run.save_dir) / "weights"
    best_weights = weights_dir / "best.pt"
    print(f"Training complete. Best weights: {best_weights}")


if __name__ == "__main__":
    main()

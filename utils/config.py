from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    base_dir: Path
    processed_dir: Path
    artifact_dir: Path
    models_dir: Path
    metrics_dir: Path
    predictions_dir: Path
    plots_dir: Path
    data_artifact_dir: Path


def locate_project_base() -> Path:
    env_override = os.getenv("OLIST_APP_BASE_DIR")
    if env_override:
        path = Path(env_override).expanduser().resolve()
        if path.exists():
            return path

    candidates = [
        Path.cwd(),
        Path.cwd().parent,
        Path.cwd().parent.parent,
        Path(__file__).resolve().parent.parent,
        Path(__file__).resolve().parent.parent.parent,
    ]
    for base in candidates:
        if (base / "artifacts").exists() and (base / "data").exists():
            return base.resolve()

    return Path.cwd().resolve()


def get_paths() -> AppPaths:
    base_dir = locate_project_base()
    artifact_dir = base_dir / "artifacts"
    processed_dir = base_dir / "data" / "processed"

    return AppPaths(
        base_dir=base_dir,
        processed_dir=processed_dir,
        artifact_dir=artifact_dir,
        models_dir=artifact_dir / "models",
        metrics_dir=artifact_dir / "metrics",
        predictions_dir=artifact_dir / "predictions",
        plots_dir=artifact_dir / "plots",
        data_artifact_dir=artifact_dir / "data",
    )

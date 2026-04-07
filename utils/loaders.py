from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Iterable

import joblib
import pandas as pd
import streamlit as st

from utils.config import get_paths


def _deduplicate_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    unique_paths: list[Path] = []
    for path in paths:
        key = str(path)
        if key not in seen:
            unique_paths.append(path)
            seen.add(key)
    return unique_paths


def _first_existing_path(candidates: Iterable[Path]) -> Path | None:
    for path in _deduplicate_paths(candidates):
        if path.exists():
            return path
    return None


def _table_candidates(base_dir: Path, name_or_stem: str) -> list[Path]:
    requested = Path(name_or_stem)

    if requested.is_absolute():
        if requested.suffix:
            return [requested]
        return [requested.with_suffix(".parquet"), requested.with_suffix(".csv"), requested]

    if requested.suffix in {".parquet", ".csv"}:
        return [base_dir / requested]

    return [
        base_dir / f"{name_or_stem}.parquet",
        base_dir / f"{name_or_stem}.csv",
        base_dir / name_or_stem,
    ]


def _json_candidates(base_dir: Path, filename: str) -> list[Path]:
    requested = Path(filename)

    if requested.is_absolute():
        if requested.suffix:
            return [requested]
        return [requested.with_suffix(".json"), requested]

    if requested.suffix == ".json":
        return [base_dir / requested]

    return [base_dir / f"{filename}.json", base_dir / filename]


def _generic_candidates(base_dir: Path, filename: str) -> list[Path]:
    requested = Path(filename)
    if requested.is_absolute():
        return [requested]
    return [base_dir / requested]


def _read_table(path: Path) -> pd.DataFrame | None:
    try:
        if path.suffix.lower() == ".parquet":
            return pd.read_parquet(path)
        if path.suffix.lower() == ".csv":
            return pd.read_csv(path)
    except Exception:
        return None
    return None


def _read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def load_processed_table(stem: str) -> pd.DataFrame | None:
    paths = get_paths()
    path = _first_existing_path(_table_candidates(paths.processed_dir, stem))
    if path is None:
        return None
    return _read_table(path)


@st.cache_data(show_spinner=False)
def load_metric_csv(filename: str) -> pd.DataFrame | None:
    paths = get_paths()
    path = _first_existing_path(_table_candidates(paths.metrics_dir, filename))
    if path is None:
        return None
    return _read_table(path)


@st.cache_data(show_spinner=False)
def load_prediction_csv(filename: str) -> pd.DataFrame | None:
    paths = get_paths()
    path = _first_existing_path(_table_candidates(paths.predictions_dir, filename))
    if path is None:
        return None
    return _read_table(path)


@st.cache_data(show_spinner=False)
def load_data_artifact_csv(filename: str) -> pd.DataFrame | None:
    paths = get_paths()
    path = _first_existing_path(_table_candidates(paths.data_artifact_dir, filename))
    if path is None:
        return None
    return _read_table(path)


@st.cache_data(show_spinner=False)
def load_metric_json(filename: str) -> dict[str, Any] | list[Any] | None:
    paths = get_paths()
    path = _first_existing_path(_json_candidates(paths.metrics_dir, filename))
    if path is None:
        return None
    return _read_json(path)


@st.cache_data(show_spinner=False)
def load_prediction_json(filename: str) -> dict[str, Any] | list[Any] | None:
    paths = get_paths()
    path = _first_existing_path(_json_candidates(paths.predictions_dir, filename))
    if path is None:
        return None
    return _read_json(path)


@st.cache_data(show_spinner=False)
def load_model_json(filename: str) -> dict[str, Any] | list[Any] | None:
    paths = get_paths()
    path = _first_existing_path(_json_candidates(paths.models_dir, filename))
    if path is None:
        return None
    return _read_json(path)


@st.cache_data(show_spinner=False)
def load_summary_json(filename: str) -> dict[str, Any] | list[Any] | None:
    return load_metric_json(filename)


@st.cache_data(show_spinner=False)
def load_integration_payload() -> dict[str, Any] | list[Any] | None:
    return load_prediction_json("integration_ui_payload_preview.json")


@st.cache_resource(show_spinner=False)
def load_joblib_model(filename: str) -> Any | None:
    paths = get_paths()
    path = _first_existing_path(_generic_candidates(paths.models_dir, filename))
    if path is None:
        return None
    try:
        return joblib.load(path)
    except Exception:
        return None


@st.cache_resource(show_spinner=False)
def load_pickle_model(filename: str) -> Any | None:
    paths = get_paths()
    path = _first_existing_path(_generic_candidates(paths.models_dir, filename))
    if path is None:
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def load_text_asset(filename: str) -> str | None:
    paths = get_paths()
    search_dirs = (
        paths.artifact_dir,
        paths.metrics_dir,
        paths.predictions_dir,
        paths.data_artifact_dir,
        paths.processed_dir,
    )

    candidates: list[Path] = []
    for base_dir in search_dirs:
        candidates.extend(_generic_candidates(base_dir, filename))

    path = _first_existing_path(candidates)
    if path is None:
        return None
    return _read_text(path)


@st.cache_data(show_spinner=False)
def load_plot_path(filename: str) -> str | None:
    paths = get_paths()
    path = _first_existing_path(_generic_candidates(paths.plots_dir, filename))
    if path is None:
        return None
    return str(path)


def file_exists(path_like: str | Path) -> bool:
    path = Path(path_like)
    if path.exists():
        return True

    paths = get_paths()
    candidates = [
        paths.base_dir / path,
        paths.artifact_dir / path,
        paths.processed_dir / path,
        paths.metrics_dir / path,
        paths.predictions_dir / path,
        paths.models_dir / path,
        paths.data_artifact_dir / path,
        paths.plots_dir / path,
    ]
    return _first_existing_path(candidates) is not None


def resolve_file(path_like: str | Path) -> Path | None:
    path = Path(path_like)
    if path.exists():
        return path

    paths = get_paths()
    candidates = [
        paths.base_dir / path,
        paths.artifact_dir / path,
        paths.processed_dir / path,
        paths.metrics_dir / path,
        paths.predictions_dir / path,
        paths.models_dir / path,
        paths.data_artifact_dir / path,
        paths.plots_dir / path,
    ]
    return _first_existing_path(candidates)


def describe_file(path_like: str | Path) -> dict[str, Any]:
    path = resolve_file(path_like)
    exists = path is not None
    return {
        "path": str(path_like if path is None else path),
        "exists": exists,
        "size_kb": round(path.stat().st_size / 1024, 2) if exists and path is not None else None,
        "suffix": path.suffix.lower() if exists and path is not None and path.suffix else None,
    }


def _module_registry() -> dict[str, dict[str, list[Path]]]:
    paths = get_paths()
    return {
        "dashboard": {
            "required": [
                paths.processed_dir / "orders_base_final.parquet",
            ],
            "demo": [
                paths.processed_dir / "orders_base_final.csv",
            ],
        },
        "segmentation": {
            "required": [
                paths.processed_dir / "rfm_df.parquet",
                paths.models_dir / "rfm_standard_scaler.joblib",
                paths.models_dir / "kmeans_model.joblib",
                paths.metrics_dir / "kmeans_cluster_profile.csv",
            ],
            "demo": [
                paths.predictions_dir / "rfm_clustered_kmeans.csv",
            ],
        },
        "recommendation": {
            "required": [
                paths.models_dir / "best_surprise_model.pkl",
                paths.models_dir / "surprise_deployment_bundle.pkl",
                paths.models_dir / "seen_items_map.pkl",
            ],
            "demo": [
                paths.predictions_dir / "integration_ui_payload_preview.json",
                paths.predictions_dir / "popular_products_fallback.csv",
                paths.predictions_dir / "sample_product_neighbors.csv",
            ],
        },
        "market_basket": {
            "required": [
                paths.metrics_dir / "association_rules.csv",
                paths.metrics_dir / "frequent_itemsets.csv",
            ],
            "demo": [],
        },
        "prediction": {
            "required": [
                paths.models_dir / "best_classifier_baseline.joblib",
                paths.models_dir / "best_classifier_text_tfidf.joblib",
                paths.models_dir / "best_regressor_baseline.joblib",
            ],
            "demo": [
                paths.predictions_dir / "integration_ui_payload_preview.json",
            ],
        },
        "admin": {
            "required": [],
            "demo": [],
        },
    }


def evaluate_artifact_group(required: Iterable[Path], demo: Iterable[Path] | None = None) -> dict[str, Any]:
    required = list(required)
    demo = list(demo or [])
    found_required = [str(path) for path in required if path.exists()]
    missing_required = [str(path) for path in required if not path.exists()]
    found_demo = [str(path) for path in demo if path.exists()]
    if not missing_required:
        status = "ready"
    elif found_demo:
        status = "demo"
    else:
        status = "missing"
    return {
        "status": status,
        "required_total": len(required),
        "required_found": len(found_required),
        "demo_total": len(demo),
        "demo_found": len(found_demo),
        "missing_required": missing_required,
    }


@st.cache_data(show_spinner=False)
def get_module_statuses() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for module_name, config in _module_registry().items():
        summary = evaluate_artifact_group(required=config.get("required", []), demo=config.get("demo", []))
        rows.append(
            {
                "module": module_name,
                "status": summary["status"],
                "required_found": f"{summary['required_found']}/{summary['required_total']}",
                "demo_found": f"{summary['demo_found']}/{summary['demo_total']}",
                "missing_required": summary["missing_required"],
            }
        )
    return rows


def get_module_status(module_name: str) -> dict[str, Any]:
    registry = _module_registry()
    if module_name not in registry:
        return {
            "status": "missing",
            "required_total": 0,
            "required_found": 0,
            "demo_total": 0,
            "demo_found": 0,
            "missing_required": [f"Unknown module: {module_name}"],
        }
    config = registry[module_name]
    return evaluate_artifact_group(required=config.get("required", []), demo=config.get("demo", []))


def clear_loader_caches() -> None:
    st.cache_data.clear()
    st.cache_resource.clear()

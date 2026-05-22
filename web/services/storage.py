import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from django.conf import settings


DATASET_KIND_RAW = "raw"
DATASET_KIND_CLEANED = "cleaned"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def data_root() -> Path:
    return Path(settings.BASE_DIR) / "data"


def datasets_root() -> Path:
    return data_root() / "datasets"


def model_runs_root() -> Path:
    return data_root() / "model_runs"


def ensure_dirs() -> None:
    (datasets_root()).mkdir(parents=True, exist_ok=True)
    (model_runs_root()).mkdir(parents=True, exist_ok=True)


def dataset_dir(dataset_id: str) -> Path:
    return datasets_root() / dataset_id


def model_run_dir(model_run_id: str) -> Path:
    return model_runs_root() / model_run_id


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def create_raw_dataset(uploaded_file, *, original_name: str) -> Tuple[str, Path]:
    ensure_dirs()
    dataset_id = str(uuid4())
    ddir = dataset_dir(dataset_id)
    ddir.mkdir(parents=True, exist_ok=True)
    raw_path = ddir / "raw.csv"
    with raw_path.open("wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)
    write_json(
        ddir / "meta.json",
        {
            "dataset_id": dataset_id,
            "kind": DATASET_KIND_RAW,
            "source_dataset_id": None,
            "original_name": original_name,
            "created_at": _now_iso(),
            "file": "raw.csv",
        },
    )
    return dataset_id, raw_path


def create_cleaned_dataset(source_dataset_id: str, *, original_name: Optional[str] = None) -> Tuple[str, Path]:
    ensure_dirs()
    dataset_id = str(uuid4())
    ddir = dataset_dir(dataset_id)
    ddir.mkdir(parents=True, exist_ok=True)
    cleaned_path = ddir / "cleaned.csv"
    write_json(
        ddir / "meta.json",
        {
            "dataset_id": dataset_id,
            "kind": DATASET_KIND_CLEANED,
            "source_dataset_id": source_dataset_id,
            "original_name": original_name,
            "created_at": _now_iso(),
            "file": "cleaned.csv",
        },
    )
    return dataset_id, cleaned_path


def dataset_meta(dataset_id: str) -> Dict[str, Any]:
    ddir = dataset_dir(dataset_id)
    return read_json(ddir / "meta.json")


def dataset_csv_path(dataset_id: str) -> Path:
    meta = dataset_meta(dataset_id)
    ddir = dataset_dir(dataset_id)
    return ddir / meta["file"]


def create_model_run(dataset_id: str, *, model_name: str) -> str:
    ensure_dirs()
    model_run_id = str(uuid4())
    mdir = model_run_dir(model_run_id)
    mdir.mkdir(parents=True, exist_ok=True)
    write_json(
        mdir / "meta.json",
        {
            "model_run_id": model_run_id,
            "dataset_id": dataset_id,
            "model_name": model_name,
            "created_at": _now_iso(),
            "artifact": "model.joblib",
            "metrics": None,
        },
    )
    return model_run_id


def update_model_run_metrics(model_run_id: str, metrics: Dict[str, Any]) -> None:
    mdir = model_run_dir(model_run_id)
    meta_path = mdir / "meta.json"
    meta = read_json(meta_path)
    meta["metrics"] = metrics
    write_json(meta_path, meta)


def model_run_meta(model_run_id: str) -> Dict[str, Any]:
    return read_json(model_run_dir(model_run_id) / "meta.json")


def model_artifact_path(model_run_id: str) -> Path:
    meta = model_run_meta(model_run_id)
    return model_run_dir(model_run_id) / meta["artifact"]


from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .errors import UserFacingError


@dataclass(frozen=True)
class TrainOptions:
    target_col: str = ""
    test_size: float = 0.2
    random_state: int = 42


def _as_int_labels(series: pd.Series) -> np.ndarray:
    try:
        return series.astype(int).to_numpy()
    except Exception:  # noqa: BLE001
        raise UserFacingError("目标列无法转换为0/1整数标签，请检查数据。")


def build_logreg_pipeline(numeric_cols: List[str], categorical_cols: List[str]) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("num", Pipeline(steps=[("scaler", StandardScaler())]), numeric_cols),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical_cols,
            ),
        ],
        remainder="drop",
    )
    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        solver="lbfgs",
    )
    return Pipeline(steps=[("preprocess", preprocess), ("model", model)])


def build_rf_pipeline(numeric_cols: List[str], categorical_cols: List[str]) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("num", "passthrough", numeric_cols),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical_cols,
            ),
        ],
        remainder="drop",
    )
    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced_subsample",
    )
    return Pipeline(steps=[("preprocess", preprocess), ("model", model)])


def train_classifier(df: pd.DataFrame, options: TrainOptions, *, model: str) -> Tuple[Pipeline, Dict[str, Any]]:
    if not options.target_col:
        raise UserFacingError("请先选择目标列后再训练模型。")
    if options.target_col not in df.columns:
        raise UserFacingError(f"数据集中不存在目标列：{options.target_col}")

    y = _as_int_labels(df[options.target_col])
    X = df.drop(columns=[options.target_col]).copy()

    numeric_cols = [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])]
    categorical_cols = [c for c in X.columns if c not in numeric_cols]

    unique_labels = sorted(set(int(v) for v in np.unique(y)))
    if unique_labels not in ([0, 1], [0], [1]):
        raise UserFacingError(f"目标列应为二分类0/1，当前类别：{unique_labels}")
    if len(unique_labels) < 2:
        raise UserFacingError("目标列只有一个类别（全0或全1），无法训练分类模型。")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=options.test_size,
        random_state=options.random_state,
        stratify=y,
    )

    if model == "logistic_regression":
        pipe = build_logreg_pipeline(numeric_cols=numeric_cols, categorical_cols=categorical_cols)
    elif model == "random_forest":
        pipe = build_rf_pipeline(numeric_cols=numeric_cols, categorical_cols=categorical_cols)
    else:
        raise UserFacingError(f"不支持的模型：{model}")
    pipe.fit(X_train, y_train)

    proba = pipe.predict_proba(X_test)[:, 1]
    y_pred = (proba >= 0.5).astype(int)

    metrics: Dict[str, Any] = {
        "model": model,
        "target_col": options.target_col,
        "test_size": options.test_size,
        "random_state": options.random_state,
        "label_counts": {"train": _label_counts(y_train), "test": _label_counts(y_test)},
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(_safe_auc(y_test, proba)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "threshold_default": 0.5,
        "features": {"numeric": numeric_cols, "categorical": categorical_cols},
    }
    return pipe, metrics


def _label_counts(y: np.ndarray) -> Dict[str, int]:
    y = y.astype(int)
    return {"0": int((y == 0).sum()), "1": int((y == 1).sum())}


def _safe_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    try:
        return roc_auc_score(y_true, y_score)
    except Exception:  # noqa: BLE001
        return float("nan")


def predict_proba(pipe: Pipeline, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(rows) == 0:
        raise UserFacingError("rows 不能为空")
    X = pd.DataFrame(rows)
    proba = pipe.predict_proba(X)[:, 1]
    return {"proba": [float(p) for p in proba]}

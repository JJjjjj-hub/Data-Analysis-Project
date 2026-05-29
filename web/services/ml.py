from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    make_scorer,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .errors import UserFacingError


def _linear_f1_scorer(estimator, X, y_true):
    """自定义f1评分器：将线性回归连续输出裁剪到[0,1]后按0.5阈值二值化，供GridSearchCV使用"""
    raw_pred = estimator.predict(X)
    proba = np.clip(raw_pred, 0.0, 1.0)
    y_pred = (proba >= 0.5).astype(int)
    return f1_score(y_true, y_pred, zero_division=0)


@dataclass(frozen=True)
class TrainOptions:
    target_col: str = "depression_label"
    test_size: float = 0.2
    random_state: int = 42
    enable_cv: bool = False
    cv_folds: int = 3


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


def build_linear_pipeline(numeric_cols: List[str], categorical_cols: List[str]) -> Pipeline:
    """构建线性回归管道"""
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
    model = LinearRegression()
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
    elif model == "linear_regression":
        pipe = build_linear_pipeline(numeric_cols=numeric_cols, categorical_cols=categorical_cols)
    elif model == "random_forest":
        pipe = build_rf_pipeline(numeric_cols=numeric_cols, categorical_cols=categorical_cols)
    else:
        raise UserFacingError(f"不支持的模型：{model}")

    # 超参数调优（可选）
    cv_results = None
    if options.enable_cv:
        pipe, cv_results = _tune_hyperparams(
            pipe, X_train, y_train, model,
            options.cv_folds, options.random_state,
        )
    else:
        pipe.fit(X_train, y_train)

    if model == "linear_regression":
        raw_pred = pipe.predict(X_test)
        proba = np.clip(raw_pred, 0.0, 1.0)
    else:
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

    # 添加CV结果
    if cv_results:
        metrics["best_params"] = cv_results["best_params"]
        metrics["cv_scores"] = cv_results["cv_scores"]

    # 添加特征重要性
    all_feature_names = numeric_cols + categorical_cols
    metrics["feature_importance"] = _extract_feature_importance(pipe, all_feature_names, model)

    return pipe, metrics


def _label_counts(y: np.ndarray) -> Dict[str, int]:
    y = y.astype(int)
    return {"0": int((y == 0).sum()), "1": int((y == 1).sum())}


def _safe_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    try:
        return roc_auc_score(y_true, y_score)
    except Exception:  # noqa: BLE001
        return float("nan")


def _tune_hyperparams(
    pipe: Pipeline,
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    model: str,
    cv_folds: int,
    random_state: int,
) -> Tuple[Pipeline, Dict[str, Any]]:
    """使用GridSearchCV搜索最优超参数"""
    scoring = "f1"
    if model == "logistic_regression":
        param_grid = {
            'model__C': [0.01, 0.1, 1.0, 10.0],
            'model__class_weight': ['balanced', None],
        }
    elif model == "linear_regression":
        param_grid = {
            'model__fit_intercept': [True, False],
        }
        # 线性回归输出连续值，需用自定义scorer转为二分类后再算F1
        scoring = make_scorer(_linear_f1_scorer)
    elif model == "random_forest":
        param_grid = {
            'model__n_estimators': [100, 200, 300],
            'model__max_depth': [5, 10, None],
            'model__min_samples_split': [2, 5],
        }
    else:
        return pipe, None

    grid_search = GridSearchCV(
        pipe,
        param_grid,
        cv=cv_folds,
        scoring=scoring,
        n_jobs=-1,
    )
    grid_search.fit(X_train, y_train)

    cv_results = {
        "best_params": grid_search.best_params_,
        "cv_scores": {
            "mean_f1": float(grid_search.cv_results_['mean_test_score'][grid_search.best_index_]),
            "std_f1": float(grid_search.cv_results_['std_test_score'][grid_search.best_index_]),
            "scores": [
                float(grid_search.cv_results_[f'split{i}_test_score'][grid_search.best_index_])
                for i in range(cv_folds)
            ],
        },
    }

    return grid_search.best_estimator_, cv_results


def _extract_feature_importance(
    pipe: Pipeline,
    feature_names: List[str],
    model: str,
) -> List[Dict[str, Any]]:
    """提取特征重要性（逻辑回归/线性回归返回系数，随机森林返回feature_importances_）"""
    if model == "logistic_regression" or model == "linear_regression":
        raw_coef = pipe.named_steps['model'].coef_
        # LogisticRegression.coef_ 是 (1, n_features)，LinearRegression.coef_ 是 (n_features,)
        coef = raw_coef[0] if raw_coef.ndim == 2 else raw_coef

        try:
            transformed_features = pipe.named_steps['preprocess'].get_feature_names_out()
        except Exception:
            transformed_features = feature_names

        importance_list = []
        for name, value in zip(transformed_features, coef):
            importance_list.append({
                "feature": name,
                "importance": float(abs(value)),
                "raw_value": float(value),
                "type": "positive" if value > 0 else "negative" if value < 0 else "neutral",
            })

        # 按绝对值降序排列
        importance_list.sort(key=lambda x: x["importance"], reverse=True)

    elif model == "random_forest":
        importances = pipe.named_steps['model'].feature_importances_

        try:
            transformed_features = pipe.named_steps['preprocess'].get_feature_names_out()
        except Exception:
            transformed_features = feature_names

        importance_list = []
        for name, value in zip(transformed_features, importances):
            importance_list.append({
                "feature": name,
                "importance": float(value),
                "raw_value": float(value),
                "type": "importance",
            })

        importance_list.sort(key=lambda x: x["importance"], reverse=True)

    return importance_list[:10]


def predict_proba(pipe: Pipeline, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(rows) == 0:
        raise UserFacingError("rows 不能为空")
    X = pd.DataFrame(rows)
    try:
        proba = pipe.predict_proba(X)[:, 1]
    except AttributeError:
        raw_pred = pipe.predict(X)
        proba = np.clip(raw_pred, 0.0, 1.0)
    return {"proba": [float(p) for p in proba]}
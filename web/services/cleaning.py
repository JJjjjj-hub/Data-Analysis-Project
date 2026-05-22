from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CleaningOptions:
    target_col: str = "depression_label"
    missing_strategy: str = "auto"  # auto | drop_rows
    outlier_strategy: str = "iqr_clip"  # none | iqr_clip | iqr_drop_rows
    normalize_categories: bool = True


def _mode(series: pd.Series) -> Optional[Any]:
    try:
        values = series.dropna().mode()
        if len(values) == 0:
            return None
        return values.iloc[0]
    except Exception:  # noqa: BLE001
        return None


def _iqr_bounds(series: pd.Series, *, k: float = 1.5) -> Tuple[float, float]:
    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def clean_dataframe(df: pd.DataFrame, options: CleaningOptions) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    report: Dict[str, Any] = {
        "rows_before": int(df.shape[0]),
        "cols_before": int(df.shape[1]),
        "missing": {},
        "outliers": {},
        "normalized_categories": False,
        "rows_after": None,
        "cols_after": None,
        "notes": [],
    }

    df_clean = df.copy()

    if options.normalize_categories:
        cat_cols = [c for c in df_clean.columns if df_clean[c].dtype == object]
        for col in cat_cols:
            df_clean[col] = df_clean[col].astype(str).str.strip()
            df_clean[col] = df_clean[col].replace({"nan": np.nan, "None": np.nan, "": np.nan})
            df_clean[col] = df_clean[col].str.lower()
        report["normalized_categories"] = True

    missing_by_col = df_clean.isna().sum().to_dict()
    report["missing"] = {str(k): int(v) for k, v in missing_by_col.items()}

    if options.missing_strategy == "drop_rows":
        df_clean = df_clean.dropna()
        report["notes"].append("missing_strategy=drop_rows")
    else:
        numeric_cols = [c for c in df_clean.columns if pd.api.types.is_numeric_dtype(df_clean[c])]
        if options.target_col in numeric_cols:
            numeric_cols = [c for c in numeric_cols if c != options.target_col]
        cat_cols = [c for c in df_clean.columns if c not in numeric_cols]
        for col in numeric_cols:
            if df_clean[col].isna().any():
                df_clean[col] = df_clean[col].fillna(df_clean[col].median())
        for col in cat_cols:
            if df_clean[col].isna().any():
                m = _mode(df_clean[col])
                if m is not None:
                    df_clean[col] = df_clean[col].fillna(m)
        report["notes"].append("missing_strategy=auto")

    if options.outlier_strategy in {"iqr_clip", "iqr_drop_rows"}:
        numeric_cols = [c for c in df_clean.columns if pd.api.types.is_numeric_dtype(df_clean[c])]
        numeric_cols = [c for c in numeric_cols if c != options.target_col]
        outlier_rows_mask = np.zeros(len(df_clean), dtype=bool)
        for col in numeric_cols:
            series = df_clean[col].astype(float)
            lower, upper = _iqr_bounds(series)
            mask = (series < lower) | (series > upper)
            count = int(mask.sum())
            if count == 0:
                continue
            report["outliers"][str(col)] = {
                "count": count,
                "lower": lower,
                "upper": upper,
                "strategy": options.outlier_strategy,
            }
            if options.outlier_strategy == "iqr_clip":
                df_clean[col] = series.clip(lower=lower, upper=upper)
            else:
                outlier_rows_mask |= mask.to_numpy()
        if options.outlier_strategy == "iqr_drop_rows" and outlier_rows_mask.any():
            df_clean = df_clean.loc[~outlier_rows_mask].copy()

    report["rows_after"] = int(df_clean.shape[0])
    report["cols_after"] = int(df_clean.shape[1])
    return df_clean, report

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd

from .errors import UserFacingError


def read_csv_flexible(path: Path) -> pd.DataFrame:
    errors = []
    for encoding in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{encoding}: {e}")
    raise UserFacingError(f"无法读取CSV（编码或格式问题）。尝试过: {', '.join(errors)}")


def dataframe_preview(df: pd.DataFrame, *, limit: int = 20) -> Tuple[list[str], list[dict]]:
    df_preview = df.head(limit).copy()
    df_preview = df_preview.where(pd.notnull(df_preview), None)
    columns = [str(c) for c in df_preview.columns.tolist()]
    rows = df_preview.to_dict(orient="records")
    return columns, rows


def infer_column_kinds(df: pd.DataFrame, *, target_col: str | None = None) -> dict:
    kinds = {}
    for col in df.columns:
        col_name = str(col)
        if target_col and col_name == target_col:
            kinds[col_name] = "target"
            continue
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            kinds[col_name] = "numeric"
        else:
            kinds[col_name] = "categorical"
    return kinds


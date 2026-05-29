from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import pandas as pd
from django.http import FileResponse
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .services.cleaning import CleaningOptions, clean_dataframe
from .services.csv_io import dataframe_preview, infer_column_kinds, read_csv_flexible
from .services.errors import UserFacingError
from .services.ml import TrainOptions, predict_proba, train_classifier
from .services.storage import (
    create_cleaned_dataset,
    create_model_run,
    create_raw_dataset,
    dataset_csv_path,
    dataset_dir,
    dataset_meta,
    ensure_dataset_owner,
    ensure_model_run_owner,
    model_artifact_path,
    model_run_meta,
    update_model_run_metrics,
    write_json,
)


def _bad_request(message: str, *, code: str = "bad_request", status: int = 400) -> Response:
    return Response({"ok": False, "error": {"code": code, "message": message}}, status=status)


def _ok(payload: Dict[str, Any], *, status: int = 200) -> Response:
    return Response({"ok": True, **payload}, status=status)

def _max_upload_size_bytes() -> int:
    return 10 * 1024 * 1024


def _get_target_col(request) -> str:
    return (request.data.get("target_col") or "depression_label").strip()

def _parse_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y", "on"}:
            return True
        if v in {"0", "false", "no", "n", "off"}:
            return False
    return default


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def dataset_upload(request):
    try:
        uploaded = request.FILES.get("file")
        if uploaded is None:
            return _bad_request("缺少上传文件字段 file")
        if uploaded.size and uploaded.size > _max_upload_size_bytes():
            return _bad_request("文件过大（>10MB）")
        name = getattr(uploaded, "name", "uploaded.csv")
        if not name.lower().endswith(".csv"):
            return _bad_request("仅支持CSV文件（.csv）")

        dataset_id, raw_path = create_raw_dataset(
            uploaded,
            original_name=name,
            owner_id=request.user.id,
            owner_username=request.user.username,
        )
        df = read_csv_flexible(raw_path)

        target_col = _get_target_col(request)
        col_kinds = infer_column_kinds(df, target_col=target_col if target_col in df.columns else None)
        columns, rows = dataframe_preview(df, limit=20)

        write_json(
            dataset_dir(dataset_id) / "schema.json",
            {
                "columns": columns,
                "column_kinds": col_kinds,
                "row_count": int(df.shape[0]),
                "col_count": int(df.shape[1]),
            },
        )

        return _ok(
            {
                "dataset_id": dataset_id,
                "columns": columns,
                "column_kinds": col_kinds,
                "preview_rows": rows,
                "row_count": int(df.shape[0]),
            },
            status=201,
        )
    except UserFacingError as e:
        return _bad_request(e.message, code=e.code, status=e.status)
    except Exception as e:  # noqa: BLE001
        return _bad_request(f"上传解析失败：{e}")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def dataset_clean(request, dataset_id: str):
    try:
        target_col = (request.data.get("target_col") or "depression_label").strip()
        missing_strategy = (request.data.get("missing_strategy") or "auto").strip()
        outlier_strategy = (request.data.get("outlier_strategy") or "iqr_clip").strip()
        normalize_categories = _parse_bool(request.data.get("normalize_categories"), True)

        meta = ensure_dataset_owner(dataset_id, owner_id=request.user.id, owner_username=request.user.username)
        if meta.get("owner_id") != request.user.id:
            return _bad_request("无权访问该数据集", code="forbidden", status=403)

        src_path = dataset_csv_path(dataset_id)
        df = read_csv_flexible(src_path)

        options = CleaningOptions(
            target_col=target_col,
            missing_strategy=missing_strategy,
            outlier_strategy=outlier_strategy,
            normalize_categories=normalize_categories,
        )
        df_clean, report = clean_dataframe(df, options)

        cleaned_dataset_id, cleaned_path = create_cleaned_dataset(
            dataset_id,
            original_name=dataset_meta(dataset_id).get("original_name"),
            owner_id=request.user.id,
            owner_username=request.user.username,
        )
        cleaned_path.parent.mkdir(parents=True, exist_ok=True)
        df_clean.to_csv(cleaned_path, index=False)
        write_json(dataset_dir(cleaned_dataset_id) / "clean_report.json", report)

        columns, rows = dataframe_preview(df_clean, limit=20)
        col_kinds = infer_column_kinds(df_clean, target_col=target_col if target_col in df_clean.columns else None)

        return _ok(
            {
                "cleaned_dataset_id": cleaned_dataset_id,
                "clean_report": report,
                "columns": columns,
                "column_kinds": col_kinds,
                "preview_rows": rows,
                "row_count": int(df_clean.shape[0]),
            }
        )
    except FileNotFoundError:
        return _bad_request("dataset_id 不存在或文件缺失", code="not_found", status=404)
    except UserFacingError as e:
        return _bad_request(e.message, code=e.code, status=e.status)
    except Exception as e:  # noqa: BLE001
        return _bad_request(f"清洗失败：{e}")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def dataset_train(request, dataset_id: str):
    try:
        target_col = (request.data.get("target_col") or "depression_label").strip()
        model_name = (request.data.get("model") or "logistic_regression").strip()
        test_size = float(request.data.get("test_size") or 0.2)
        random_state = int(request.data.get("random_state") or 42)
        enable_cv = _parse_bool(request.data.get("enable_cv"), False)
        cv_folds = int(request.data.get("cv_folds") or 3)

        if model_name not in {"logistic_regression", "linear_regression", "random_forest"}:
            return _bad_request("model 仅支持 logistic_regression / linear_regression / random_forest")

        if cv_folds < 2 or cv_folds > 5:
            return _bad_request("cv_folds 必须在 2-5 之间")

        meta = ensure_dataset_owner(dataset_id, owner_id=request.user.id, owner_username=request.user.username)
        if meta.get("owner_id") != request.user.id:
            return _bad_request("无权访问该数据集", code="forbidden", status=403)

        src_path = dataset_csv_path(dataset_id)
        df = read_csv_flexible(src_path)

        pipe, metrics = train_classifier(
            df,
            TrainOptions(target_col=target_col, test_size=test_size, random_state=random_state,
                         enable_cv=enable_cv, cv_folds=cv_folds),
            model=model_name,
        )
        model_run_id = create_model_run(
            dataset_id,
            model_name=model_name,
            owner_id=request.user.id,
            owner_username=request.user.username,
        )
        artifact_path = model_artifact_path(model_run_id)
        joblib.dump(pipe, artifact_path)
        update_model_run_metrics(model_run_id, metrics)

        return _ok({"model_run_id": model_run_id, "metrics": metrics})
    except FileNotFoundError:
        return _bad_request("dataset_id 不存在或文件缺失", code="not_found", status=404)
    except UserFacingError as e:
        return _bad_request(e.message, code=e.code, status=e.status)
    except Exception as e:  # noqa: BLE001
        return _bad_request(f"训练失败：{e}")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def model_predict(request, model_run_id: str):
    try:
        meta = ensure_model_run_owner(model_run_id, owner_id=request.user.id, owner_username=request.user.username)
        if meta.get("owner_id") != request.user.id:
            return _bad_request("无权访问该模型", code="forbidden", status=403)

        artifact_path = model_artifact_path(model_run_id)
        if not artifact_path.exists():
            return _bad_request("模型文件不存在", code="not_found", status=404)

        rows = request.data.get("rows")
        if not isinstance(rows, list):
            return _bad_request("rows 必须是对象数组")

        threshold = request.data.get("threshold")
        threshold_value: Optional[float] = None
        if threshold is not None:
            threshold_value = float(threshold)

        pipe = joblib.load(artifact_path)
        out = predict_proba(pipe, rows)
        proba = out["proba"]
        if threshold_value is None:
            threshold_value = float((meta.get("metrics") or {}).get("threshold_default") or 0.5)
        labels = [1 if p >= threshold_value else 0 for p in proba]
        return _ok({"proba": proba, "labels": labels, "threshold": threshold_value})
    except FileNotFoundError:
        return _bad_request("model_run_id 不存在", code="not_found", status=404)
    except UserFacingError as e:
        return _bad_request(e.message, code=e.code, status=e.status)
    except Exception as e:  # noqa: BLE001
        return _bad_request(f"预测失败：{e}")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dataset_export(request, dataset_id: str):
    try:
        meta = ensure_dataset_owner(dataset_id, owner_id=request.user.id, owner_username=request.user.username)
        if meta.get("owner_id") != request.user.id:
            return _bad_request("无权访问该数据集", code="forbidden", status=403)
        path = dataset_csv_path(dataset_id)
        filename = f"{dataset_id}.csv"
        return FileResponse(open(path, "rb"), as_attachment=True, filename=filename)  # noqa: SIM115
    except FileNotFoundError:
        return _bad_request("dataset_id 不存在或文件缺失", code="not_found", status=404)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dataset_stats(request, dataset_id: str):
    try:
        meta = ensure_dataset_owner(dataset_id, owner_id=request.user.id, owner_username=request.user.username)
        if meta.get("owner_id") != request.user.id:
            return _bad_request("无权访问该数据集", code="forbidden", status=403)
        src_path = dataset_csv_path(dataset_id)
        df = read_csv_flexible(src_path)

        kind = (request.query_params.get("kind") or "").strip()
        if kind == "count_by":
            col = (request.query_params.get("col") or "").strip()
            if not col or col not in df.columns:
                return _bad_request("col 不能为空且必须存在于数据集中")
            counts = df[col].astype(str).value_counts(dropna=False).to_dict()
            return _ok({"kind": kind, "col": col, "counts": counts})

        if kind == "box_by":
            value_col = (request.query_params.get("value_col") or "").strip()
            group_col = (request.query_params.get("group_col") or "").strip()
            if not value_col or value_col not in df.columns:
                return _bad_request("value_col 不能为空且必须存在于数据集中")
            if not group_col or group_col not in df.columns:
                return _bad_request("group_col 不能为空且必须存在于数据集中")
            if not pd.api.types.is_numeric_dtype(df[value_col]):
                return _bad_request("value_col 必须是数值列")
            payload = []
            for key, grp in df.groupby(group_col):
                vals = grp[value_col].dropna().astype(float)
                if len(vals) == 0:
                    continue
                q1 = float(vals.quantile(0.25))
                q2 = float(vals.quantile(0.50))
                q3 = float(vals.quantile(0.75))
                payload.append(
                    {
                        "group": str(key),
                        "box": [float(vals.min()), q1, q2, q3, float(vals.max())],
                    }
                )
            return _ok({"kind": kind, "value_col": value_col, "group_col": group_col, "series": payload})

        if kind == "scatter":
            x_col = (request.query_params.get("x_col") or "").strip()
            y_col = (request.query_params.get("y_col") or "").strip()
            color_col = (request.query_params.get("color_col") or "").strip() or None
            limit = int(request.query_params.get("limit") or 2000)
            for c in (x_col, y_col):
                if not c or c not in df.columns:
                    return _bad_request("x_col/y_col 不能为空且必须存在于数据集中")
                if not pd.api.types.is_numeric_dtype(df[c]):
                    return _bad_request("x_col/y_col 必须是数值列")
            df2 = df[[x_col, y_col] + ([color_col] if color_col and color_col in df.columns else [])].copy()
            df2 = df2.dropna()
            df2 = df2.head(limit)
            points = []
            for _, row in df2.iterrows():
                p: Dict[str, Any] = {"x": float(row[x_col]), "y": float(row[y_col])}
                if color_col and color_col in df2.columns:
                    p["c"] = str(row[color_col])
                points.append(p)
            return _ok({"kind": kind, "x_col": x_col, "y_col": y_col, "color_col": color_col, "points": points})

        return _bad_request("kind 不支持。可选：count_by / box_by / scatter")
    except FileNotFoundError:
        return _bad_request("dataset_id 不存在或文件缺失", code="not_found", status=404)
    except UserFacingError as e:
        return _bad_request(e.message, code=e.code, status=e.status)
    except Exception as e:  # noqa: BLE001
        return _bad_request(f"统计失败：{e}")

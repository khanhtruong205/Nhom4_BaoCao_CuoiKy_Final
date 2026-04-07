
from __future__ import annotations

from typing import Any

import pandas as pd


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def validate_required_columns(df: pd.DataFrame, required_columns: list[str]) -> tuple[bool, list[str]]:
    missing = [col for col in required_columns if col not in df.columns]
    return len(missing) == 0, missing


def validate_numeric_columns(df: pd.DataFrame, numeric_columns: list[str]) -> tuple[bool, list[str]]:
    invalid: list[str] = []
    for col in numeric_columns:
        if col not in df.columns:
            invalid.append(col)
            continue
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.isna().all():
            invalid.append(col)
    return len(invalid) == 0, invalid


def validate_non_negative_columns(df: pd.DataFrame, columns: list[str]) -> tuple[bool, list[str]]:
    failed: list[str] = []
    for col in columns:
        if col not in df.columns:
            failed.append(col)
            continue
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.dropna().lt(0).any():
            failed.append(col)
    return len(failed) == 0, failed


def validate_value_ranges(
    df: pd.DataFrame,
    rules: dict[str, tuple[float | None, float | None]],
) -> tuple[bool, dict[str, str]]:
    errors: dict[str, str] = {}
    for col, (min_value, max_value) in rules.items():
        if col not in df.columns:
            errors[col] = "Thiếu cột."
            continue
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            errors[col] = "Không có giá trị số hợp lệ."
            continue
        if min_value is not None and series.lt(min_value).any():
            errors[col] = f"Có giá trị nhỏ hơn {min_value}."
            continue
        if max_value is not None and series.gt(max_value).any():
            errors[col] = f"Có giá trị lớn hơn {max_value}."
    return len(errors) == 0, errors


def build_validation_report(
    df: pd.DataFrame,
    required_columns: list[str] | None = None,
    numeric_columns: list[str] | None = None,
    non_negative_columns: list[str] | None = None,
    range_rules: dict[str, tuple[float | None, float | None]] | None = None,
) -> dict[str, Any]:
    required_columns = required_columns or []
    numeric_columns = numeric_columns or []
    non_negative_columns = non_negative_columns or []
    range_rules = range_rules or {}

    required_ok, missing_columns = validate_required_columns(df, required_columns)
    numeric_ok, invalid_numeric = validate_numeric_columns(df, numeric_columns)
    non_negative_ok, negative_columns = validate_non_negative_columns(df, non_negative_columns)
    ranges_ok, range_errors = validate_value_ranges(df, range_rules)

    checks = {
        "required_columns": {
            "ok": required_ok,
            "details": missing_columns,
        },
        "numeric_columns": {
            "ok": numeric_ok,
            "details": invalid_numeric,
        },
        "non_negative_columns": {
            "ok": non_negative_ok,
            "details": negative_columns,
        },
        "range_rules": {
            "ok": ranges_ok,
            "details": range_errors,
        },
    }

    overall_ok = all(check["ok"] for check in checks.values())
    return {
        "ok": overall_ok,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "checks": checks,
    }


def validate_csv_contract(
    df: pd.DataFrame,
    contract_name: str,
    feature_columns: list[str] | None = None,
) -> dict[str, Any]:
    contracts: dict[str, dict[str, Any]] = {
        "rfm_upload": {
            "required_columns": ["recency_days", "frequency_orders", "monetary_value"],
            "numeric_columns": ["recency_days", "frequency_orders", "monetary_value"],
            "non_negative_columns": ["recency_days", "frequency_orders", "monetary_value"],
            "range_rules": {
                "recency_days": (0, None),
                "frequency_orders": (0, None),
                "monetary_value": (0, None),
            },
        },
        "orders_base_final_minimal": {
            "required_columns": ["customer_unique_id", "review_score", "payment_value_sum"],
            "numeric_columns": ["review_score", "payment_value_sum"],
            "non_negative_columns": ["payment_value_sum"],
            "range_rules": {
                "review_score": (1, 5),
                "payment_value_sum": (0, None),
            },
        },
        "ratings_df_minimal": {
            "required_columns": ["customer_unique_id", "product_id", "review_score"],
            "numeric_columns": ["review_score"],
            "non_negative_columns": ["review_score"],
            "range_rules": {"review_score": (1, 5)},
        },
        "transactions_df_minimal": {
            "required_columns": ["order_id", "product_category_name_english"],
        },
        "regression_input_schema": {
            "required_columns": feature_columns or [],
            "numeric_columns": [],
            "non_negative_columns": [],
            "range_rules": {},
        },
        "custom": {
            "required_columns": [],
        },
    }

    config = contracts.get(contract_name, contracts["custom"])
    return build_validation_report(
        df=df,
        required_columns=config.get("required_columns"),
        numeric_columns=config.get("numeric_columns"),
        non_negative_columns=config.get("non_negative_columns"),
        range_rules=config.get("range_rules"),
    )

from __future__ import annotations

import math
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# =========================================================
# Generic helpers
# =========================================================
def _to_dataframe(rows: list[dict] | pd.DataFrame | None) -> pd.DataFrame:
    if rows is None:
        return pd.DataFrame()
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    if isinstance(rows, list):
        return pd.DataFrame(rows)
    return pd.DataFrame()


def _safe_numeric(df: pd.DataFrame, column: str) -> pd.Series | None:
    if df is None or df.empty or column not in df.columns:
        return None
    return pd.to_numeric(df[column], errors="coerce")


def _clean_categorical(series: pd.Series, fill_value: str = "unknown") -> pd.Series:
    return series.fillna(fill_value).astype(str).str.strip().replace({"": fill_value})


def _best_count_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


# =========================================================
# Status / admin tables
# =========================================================
def summary_status_dataframe(rows: list[dict] | pd.DataFrame | None) -> pd.DataFrame:
    """
    Normalize module/artifact status rows for display in dataframe.
    Converts list-like columns into readable strings while preserving raw values when possible.
    """
    df = _to_dataframe(rows)
    if df.empty:
        return df

    out = df.copy()

    for col in ["missing_required", "missing_demo", "found_required", "found_demo"]:
        if col in out.columns:
            out[col] = out[col].apply(
                lambda x: ", ".join(map(str, x)) if isinstance(x, (list, tuple, set)) else x
            )

    if "status" in out.columns and "status_badge" not in out.columns:
        badge_map = {
            "ready": "🟢 READY",
            "demo": "🟡 DEMO",
            "missing": "🔴 MISSING",
        }
        out["status_badge"] = out["status"].astype(str).str.lower().map(badge_map).fillna("⚪ UNKNOWN")

    preferred = [
        "module",
        "status_badge",
        "status",
        "required_found",
        "demo_found",
        "available",
        "file",
        "missing_required",
    ]
    ordered = [c for c in preferred if c in out.columns] + [c for c in out.columns if c not in preferred]
    return out[ordered]


# =========================================================
# Dashboard charts
# =========================================================
def plot_review_distribution(df: pd.DataFrame):
    if df is None or df.empty or "review_score" not in df.columns:
        return None

    work = df.copy()
    work["review_score"] = pd.to_numeric(work["review_score"], errors="coerce")
    work = work.dropna(subset=["review_score"])
    if work.empty:
        return None

    counts = (
        work["review_score"]
        .astype(int)
        .value_counts()
        .sort_index()
        .reset_index()
    )
    counts.columns = ["review_score", "count"]

    fig = px.bar(
        counts,
        x="review_score",
        y="count",
        title="Review score distribution",
        labels={"review_score": "Review score", "count": "Orders"},
    )
    fig.update_layout(
        xaxis=dict(type="category"),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


def plot_payment_histogram(df: pd.DataFrame):
    target_col = "payment_value_sum" if df is not None and "payment_value_sum" in df.columns else None
    if df is None or df.empty or target_col is None:
        return None

    work = df.copy()
    work[target_col] = pd.to_numeric(work[target_col], errors="coerce")
    work = work.dropna(subset=[target_col])
    if work.empty:
        return None

    nbins = min(60, max(20, int(math.sqrt(len(work)))))
    fig = px.histogram(
        work,
        x=target_col,
        nbins=nbins,
        title="Payment value distribution",
        labels={target_col: "Payment value"},
    )
    fig.update_layout(
        bargap=0.05,
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


def plot_cluster_share(profile_df: pd.DataFrame, cluster_col: str):
    if profile_df is None or profile_df.empty or cluster_col not in profile_df.columns:
        return None

    work = profile_df.copy()
    y_col = _best_count_column(work, ["customer_count", "count", "n_customers"])
    if y_col is None:
        # fallback: count rows per cluster
        work = work[cluster_col].value_counts().reset_index()
        work.columns = [cluster_col, "customer_count"]
        y_col = "customer_count"

    work[cluster_col] = work[cluster_col].astype(str)
    fig = px.bar(
        work,
        x=cluster_col,
        y=y_col,
        title="Cluster size",
        labels={cluster_col: "Cluster", y_col: "Customers"},
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis=dict(type="category"),
    )
    return fig


def plot_top_categories(
    df: pd.DataFrame,
    column: str,
    title: str,
    top_n: int = 10,
    horizontal: bool = True,
):
    if df is None or df.empty or column not in df.columns:
        return None

    counts = (
        _clean_categorical(df[column])
        .value_counts()
        .head(top_n)
        .reset_index()
    )
    counts.columns = [column, "count"]

    if horizontal:
        fig = px.bar(
            counts.sort_values("count", ascending=True),
            x="count",
            y=column,
            orientation="h",
            title=title,
            labels={"count": "Count", column: column},
        )
    else:
        fig = px.bar(
            counts,
            x=column,
            y="count",
            title=title,
            labels={"count": "Count", column: column},
        )

    fig.update_layout(
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


def plot_order_status_distribution(df: pd.DataFrame):
    if df is None or df.empty or "order_status" not in df.columns:
        return None

    counts = (
        _clean_categorical(df["order_status"])
        .value_counts()
        .reset_index()
    )
    counts.columns = ["order_status", "count"]

    fig = px.bar(
        counts,
        x="order_status",
        y="count",
        title="Order status distribution",
        labels={"order_status": "Order status", "count": "Orders"},
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis=dict(type="category"),
    )
    return fig


def plot_monthly_orders(df: pd.DataFrame):
    if df is None or df.empty:
        return None

    work = df.copy()

    if {"purchase_year", "purchase_month"}.issubset(work.columns):
        work["purchase_year"] = pd.to_numeric(work["purchase_year"], errors="coerce")
        work["purchase_month"] = pd.to_numeric(work["purchase_month"], errors="coerce")
        work = work.dropna(subset=["purchase_year", "purchase_month"])
        if work.empty:
            return None

        work["period"] = (
            work["purchase_year"].astype(int).astype(str)
            + "-"
            + work["purchase_month"].astype(int).astype(str).str.zfill(2)
        )
        trend = work["period"].value_counts().sort_index().reset_index()
        trend.columns = ["period", "order_count"]

        fig = px.line(
            trend,
            x="period",
            y="order_count",
            markers=True,
            title="Monthly order trend",
            labels={"period": "Period", "order_count": "Orders"},
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=60, b=10),
        )
        return fig

    return None


# =========================================================
# Recommendation / FP-Growth helper charts
# =========================================================
def plot_rules_bar(
    df: pd.DataFrame,
    metric_col: str = "lift",
    label_col: str = "rule_str",
    top_n: int = 10,
    title: str | None = None,
):
    if df is None or df.empty or metric_col not in df.columns or label_col not in df.columns:
        return None

    work = df.copy()
    work[metric_col] = pd.to_numeric(work[metric_col], errors="coerce")
    work = work.dropna(subset=[metric_col])
    if work.empty:
        return None

    work = work.head(top_n).sort_values(metric_col, ascending=True)

    fig = px.bar(
        work,
        x=metric_col,
        y=label_col,
        orientation="h",
        title=title or f"Top rules by {metric_col}",
        labels={metric_col: metric_col, label_col: "Rule"},
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=60, b=10),
        yaxis=dict(categoryorder="total ascending"),
    )
    return fig


def plot_itemsets_bar(
    df: pd.DataFrame,
    label_col: str = "itemsets_str",
    value_col: str = "support",
    top_n: int = 10,
    title: str = "Top itemsets by support",
):
    if df is None or df.empty or label_col not in df.columns or value_col not in df.columns:
        return None

    work = df.copy()
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work = work.dropna(subset=[value_col])
    if work.empty:
        return None

    work = work.head(top_n).sort_values(value_col, ascending=True)

    fig = px.bar(
        work,
        x=value_col,
        y=label_col,
        orientation="h",
        title=title,
        labels={value_col: value_col, label_col: "Itemset"},
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=60, b=10),
        yaxis=dict(categoryorder="total ascending"),
    )
    return fig


# =========================================================
# KPI / metric cards
# =========================================================
def plot_metric_cards(data: dict[str, Any]):
    """
    Build a lightweight multi-card Plotly figure using Indicator traces.
    Expected input:
        {
            "Orders": 99441,
            "Customers": 93358,
            "Text F1": 0.7940,
            "Final KMeans K": 4,
        }
    """
    if not data:
        return None

    items = list(data.items())
    n = len(items)
    cols = min(4, max(1, n))
    rows = math.ceil(n / cols)

    fig = go.Figure()
    for idx, (label, value) in enumerate(items):
        row = idx // cols
        col = idx % cols

        x0 = col / cols
        x1 = (col + 1) / cols
        y1 = 1 - (row / rows)
        y0 = 1 - ((row + 1) / rows)

        if isinstance(value, float):
            # heuristic formatting
            if abs(value) >= 1000:
                value_format = ",.0f"
            elif abs(value) >= 1:
                value_format = ",.2f"
            else:
                value_format = ".4f"
        else:
            value_format = ","

        fig.add_trace(
            go.Indicator(
                mode="number",
                value=float(value) if isinstance(value, (int, float)) else 0,
                number={"valueformat": value_format},
                title={"text": f"<b>{label}</b>"},
                domain={"x": [x0, x1], "y": [y0, y1]},
            )
        )

    fig.update_layout(
        title="KPI overview",
        height=max(220, 160 * rows),
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig
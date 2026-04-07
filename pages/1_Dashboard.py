from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.charts import (
    plot_cluster_share,
    plot_payment_histogram,
    plot_review_distribution,
    plot_top_categories,
)
from utils.loaders import load_metric_csv, load_processed_table


st.title("📊 Dashboard tổng quan")
st.caption("Theo dõi nhanh hiệu suất bán hàng, chất lượng đơn hàng và hành vi mua sắm.")


def fmt(value, kind: str = "text", default: str = "—") -> str:
    if value is None:
        return default
    try:
        if kind == "int":
            return f"{int(value):,}"
        if kind == "float2":
            return f"{float(value):.2f}"
        return str(value)
    except Exception:
        return default


def build_monthly_orders(df: pd.DataFrame):
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
        return px.line(trend, x="period", y="order_count", markers=True, title="Xu hướng đơn hàng theo tháng")
    return None


def build_status_distribution(df: pd.DataFrame):
    if df is None or df.empty or "order_status" not in df.columns:
        return None
    counts = df["order_status"].fillna("unknown").astype(str).value_counts().reset_index()
    counts.columns = ["order_status", "count"]
    return px.bar(counts, x="order_status", y="count", title="Phân phối trạng thái đơn hàng")


orders_df = load_processed_table("orders_base_final")
kmeans_profile = load_metric_csv("kmeans_cluster_profile.csv")

if orders_df is None or orders_df.empty:
    st.warning("Hiện chưa có dữ liệu để hiển thị Dashboard.")
    st.stop()

with st.sidebar:
    st.markdown("## Bộ lọc")
    state_options = sorted(orders_df["customer_state"].dropna().astype(str).unique().tolist()) if "customer_state" in orders_df.columns else []
    selected_states = st.multiselect("Tỉnh / bang của khách hàng", state_options, default=[])

    category_options = sorted(orders_df["main_category"].dropna().astype(str).unique().tolist()) if "main_category" in orders_df.columns else []
    selected_categories = st.multiselect("Danh mục chính", category_options, default=[])

    status_options = sorted(orders_df["order_status"].dropna().astype(str).unique().tolist()) if "order_status" in orders_df.columns else []
    selected_statuses = st.multiselect("Trạng thái đơn hàng", status_options, default=[])

filtered_df = orders_df.copy()
if selected_states and "customer_state" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["customer_state"].astype(str).isin(selected_states)]
if selected_categories and "main_category" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["main_category"].astype(str).isin(selected_categories)]
if selected_statuses and "order_status" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["order_status"].astype(str).isin(selected_statuses)]

orders_count = len(filtered_df)
customer_count = filtered_df["customer_unique_id"].nunique() if "customer_unique_id" in filtered_df.columns else None
avg_review = pd.to_numeric(filtered_df["review_score"], errors="coerce").mean() if "review_score" in filtered_df.columns else None
avg_payment = pd.to_numeric(filtered_df["payment_value_sum"], errors="coerce").mean() if "payment_value_sum" in filtered_df.columns else None
success_rate = None
if "order_status" in filtered_df.columns and len(filtered_df) > 0:
    success_rate = (filtered_df["order_status"].astype(str).eq("delivered").mean()) * 100

top_category = None
if "main_category" in filtered_df.columns and not filtered_df.empty:
    vc = filtered_df["main_category"].dropna().astype(str).value_counts()
    if not vc.empty:
        top_category = vc.index[0]

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Đơn hàng", fmt(orders_count, "int"))
k2.metric("Khách hàng", fmt(customer_count, "int"))
k3.metric("Điểm đánh giá TB", fmt(avg_review, "float2"))
k4.metric("Giá trị đơn hàng TB", fmt(avg_payment, "float2"))
k5.metric("Tỷ lệ giao thành công", f"{fmt(success_rate, 'float2')}%" if success_rate is not None else "—")

st.subheader("Thông tin nổi bật")
h1, h2, h3 = st.columns(3)
with h1:
    with st.container(border=True):
        st.markdown("### Danh mục nổi bật")
        st.write(top_category or "Chưa xác định")
with h2:
    with st.container(border=True):
        st.markdown("### Nhóm khách hàng")
        st.write(f"{len(kmeans_profile):,} nhóm" if kmeans_profile is not None and not kmeans_profile.empty else "Chưa có dữ liệu")
with h3:
    with st.container(border=True):
        st.markdown("### Bộ lọc đang áp dụng")
        st.write(f"{len(selected_states)} khu vực • {len(selected_categories)} danh mục • {len(selected_statuses)} trạng thái")

fig1 = plot_review_distribution(filtered_df)
fig2 = plot_payment_histogram(filtered_df)
fig3 = plot_top_categories(filtered_df, "main_category", "Top danh mục chính", top_n=10)
fig4 = build_status_distribution(filtered_df)
fig5 = build_monthly_orders(filtered_df)
fig6 = plot_cluster_share(kmeans_profile, "cluster_kmeans") if kmeans_profile is not None else None

r1, r2 = st.columns(2)
with r1:
    if fig1 is not None:
        st.plotly_chart(fig1, use_container_width=True)
    if fig3 is not None:
        st.plotly_chart(fig3, use_container_width=True)
    if fig6 is not None:
        st.plotly_chart(fig6, use_container_width=True)
with r2:
    if fig2 is not None:
        st.plotly_chart(fig2, use_container_width=True)
    if fig4 is not None:
        st.plotly_chart(fig4, use_container_width=True)
    if fig5 is not None:
        st.plotly_chart(fig5, use_container_width=True)

st.subheader("Tóm tắt kinh doanh")
summary_rows = [
    {"Hạng mục": "Khách hàng", "Thông tin": f"{fmt(customer_count, 'int')} khách hàng xuất hiện trong dữ liệu đã lọc."},
    {"Hạng mục": "Chất lượng đơn hàng", "Thông tin": f"Điểm đánh giá trung bình là {fmt(avg_review, 'float2')} trên thang 5."},
    {"Hạng mục": "Giá trị đơn hàng", "Thông tin": f"Giá trị trung bình đạt {fmt(avg_payment, 'float2')}."},
    {"Hạng mục": "Vận hành", "Thông tin": f"Tỷ lệ đơn giao thành công đạt {fmt(success_rate, 'float2')}%." if success_rate is not None else "Chưa có dữ liệu vận hành."},
]
st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

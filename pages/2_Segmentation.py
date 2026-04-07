from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.inference import predict_customer_cluster
from utils.loaders import (
    load_metric_csv,
    load_plot_path,
    load_prediction_csv,
    load_processed_table,
)
from utils.validators import validate_csv_contract


st.title("👥 Phân khúc khách hàng")
st.caption("Phân nhóm khách hàng theo hành vi mua sắm để ưu tiên chăm sóc, giữ chân và tái kích hoạt.")


def fmt(value, kind: str = "text", default: str = "—") -> str:
    if value is None:
        return default
    try:
        if kind == "int":
            return f"{int(value):,}"
        if kind == "float2":
            return f"{float(value):.2f}"
        if kind == "float4":
            return f"{float(value):.4f}"
        return str(value)
    except Exception:
        return default


def cluster_col(profile_df: pd.DataFrame | None) -> str | None:
    if profile_df is None or profile_df.empty:
        return None
    for col in ["cluster_kmeans", "cluster", "cluster_label"]:
        if col in profile_df.columns:
            return col
    return None


def business_hint_from_profile(row: pd.Series) -> str:
    text_parts = []
    recency = pd.to_numeric(pd.Series([row.get("recency_days_mean")]), errors="coerce").iloc[0]
    frequency = pd.to_numeric(pd.Series([row.get("frequency_orders_mean")]), errors="coerce").iloc[0]
    monetary = pd.to_numeric(pd.Series([row.get("monetary_value_mean")]), errors="coerce").iloc[0]

    if pd.notna(frequency) and frequency >= 3:
        text_parts.append("mua thường xuyên")
    elif pd.notna(frequency) and frequency <= 1.5:
        text_parts.append("mua chưa thường xuyên")

    if pd.notna(monetary) and monetary >= 300:
        text_parts.append("chi tiêu cao")
    elif pd.notna(monetary) and monetary < 120:
        text_parts.append("chi tiêu thấp")

    if pd.notna(recency) and recency <= 60:
        text_parts.append("mới quay lại gần đây")
    elif pd.notna(recency) and recency >= 180:
        text_parts.append("lâu chưa quay lại")

    if not text_parts:
        return "Nhóm này cần xem thêm dữ liệu chi tiết để xây chính sách chăm sóc."
    return ", ".join(text_parts).capitalize() + "."


kmeans_profile = load_metric_csv("kmeans_cluster_profile.csv")
rfm_df = load_processed_table("rfm_df")
preview_clustered = load_prediction_csv("rfm_clustered_kmeans.csv")
kmeans_scatter = load_plot_path("kmeans_cluster_scatter_pca.png")

if kmeans_profile is not None and not kmeans_profile.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("Số nhóm khách hàng", fmt(len(kmeans_profile), "int"))
    if "customer_count" in kmeans_profile.columns:
        c2.metric("Khách hàng đã gán nhóm", fmt(pd.to_numeric(kmeans_profile["customer_count"], errors="coerce").sum(), "int"))
    if rfm_df is not None:
        c3.metric("Bản ghi RFM", fmt(len(rfm_df), "int"))

tab_lookup, tab_upload, tab_insights = st.tabs(["Tra cứu khách hàng", "Phân khúc từ file CSV", "Chân dung nhóm khách hàng"])

with tab_lookup:
    st.subheader("Phân tích một khách hàng")
    customer_id = st.text_input("Mã khách hàng", value="")

    if st.button("Xem phân khúc", type="primary", use_container_width=True):
        result = predict_customer_cluster(customer_id=customer_id, model_type="kmeans")
        if result["ok"]:
            left, right = st.columns([1, 1.2])
            with left:
                st.success(f"Nhóm khách hàng: {result.get('segment_name') or result['cluster']}")
                st.write(f"Mã nhóm: **{result['cluster']}**")
            with right:
                st.markdown("#### Hành vi mua sắm")
                st.dataframe(pd.DataFrame([result.get("rfm", {})]), use_container_width=True, hide_index=True)
        else:
            st.error(result["message"])

with tab_upload:
    st.subheader("Phân khúc hàng loạt từ file RFM")
    st.caption("File CSV cần có 3 cột: recency_days, frequency_orders, monetary_value.")
    uploaded = st.file_uploader("Tải lên file RFM CSV", type=["csv"])

    if uploaded is not None:
        df = pd.read_csv(uploaded)
        report = validate_csv_contract(df, "rfm_upload")
        st.dataframe(df.head(20), use_container_width=True, hide_index=True)

        if report["ok"]:
            st.success("File hợp lệ.")
        else:
            st.error("File chưa đúng cấu trúc.")
            st.json(report, expanded=False)

        if report["ok"] and st.button("Phân khúc khách hàng", type="primary"):
            rows = []
            for _, row in df.iterrows():
                result = predict_customer_cluster(rfm_row=row.to_dict(), model_type="kmeans")
                rows.append(
                    {
                        **row.to_dict(),
                        "assigned_cluster": result.get("cluster") if result["ok"] else None,
                        "segment_name": result.get("segment_name") if result["ok"] else None,
                        "error": None if result["ok"] else result.get("message"),
                    }
                )
            out = pd.DataFrame(rows)
            st.success(f"Đã xử lý {len(out):,} khách hàng.")
            st.dataframe(out, use_container_width=True, hide_index=True)
            st.download_button(
                "Tải kết quả phân khúc",
                data=out.to_csv(index=False).encode("utf-8"),
                file_name="segmentation_result.csv",
                mime="text/csv",
            )

with tab_insights:
    st.subheader("Tổng quan các nhóm khách hàng")
    if kmeans_scatter:
        st.image(kmeans_scatter, caption="Phân bố khách hàng theo không gian đặc trưng", use_container_width=True)

    if kmeans_profile is not None and not kmeans_profile.empty:
        st.markdown("#### Hồ sơ từng nhóm")
        st.dataframe(kmeans_profile, use_container_width=True, hide_index=True)

        label_col = cluster_col(kmeans_profile)
        if label_col is not None:
            explain_rows = []
            for _, row in kmeans_profile.iterrows():
                explain_rows.append(
                    {
                        "Nhóm": row.get(label_col),
                        "Tên nhóm": row.get("segment_name", f"Cluster {row.get(label_col)}"),
                        "Mô tả": business_hint_from_profile(row),
                        "Hành động gợi ý": row.get("business_strategy", "Xây ưu đãi, chăm sóc hoặc tái kích hoạt theo đặc điểm nhóm."),
                    }
                )
            st.markdown("#### Hành động đề xuất")
            st.dataframe(pd.DataFrame(explain_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có hồ sơ nhóm khách hàng.")

    if preview_clustered is not None and not preview_clustered.empty:
        with st.expander("Xem mẫu dữ liệu đã được gán nhóm", expanded=False):
            st.dataframe(preview_clustered.head(20), use_container_width=True, hide_index=True)

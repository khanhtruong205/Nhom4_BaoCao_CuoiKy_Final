from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from utils.loaders import clear_loader_caches, get_module_statuses, load_model_json
from utils.validators import validate_csv_contract


st.title("⚙️ Trung tâm vận hành")
st.caption("Dành cho người phụ trách hệ thống khi cần kiểm tra nhanh dịch vụ và xác thực file đầu vào.")


def status_label(status: str) -> str:
    return {
        "ready": "🟢 Sẵn sàng",
        "demo": "🟡 Tạm thời",
        "missing": "🔴 Cần bổ sung",
    }.get(str(status).lower(), "⚪ Chưa xác định")


module_statuses = get_module_statuses()
regression_schema = load_model_json("regression_input_schema.json")

ready_count = sum(1 for row in module_statuses if row["status"] == "ready")
demo_count = sum(1 for row in module_statuses if row["status"] == "demo")
missing_count = sum(1 for row in module_statuses if row["status"] == "missing")

k1, k2, k3 = st.columns(3)
k1.metric("Dịch vụ sẵn sàng", ready_count)
k2.metric("Dịch vụ tạm thời", demo_count)
k3.metric("Dịch vụ cần bổ sung", missing_count)

service_rows = []
name_map = {
    "dashboard": "Dashboard",
    "segmentation": "Phân khúc khách hàng",
    "recommendation": "Khuyến nghị sản phẩm",
    "market_basket": "Mua kèm thông minh",
    "prediction": "Dự đoán",
    "admin": "Trung tâm vận hành",
}
for row in module_statuses:
    service_rows.append(
        {
            "Dịch vụ": name_map.get(row["module"], row["module"]),
            "Trạng thái": status_label(row["status"]),
            "Sẵn sàng lõi": row.get("required_found", "0/0"),
        }
    )

st.subheader("Tình trạng dịch vụ")
st.dataframe(pd.DataFrame(service_rows), use_container_width=True, hide_index=True)

tab_upload, tab_tools = st.tabs(["Kiểm tra file đầu vào", "Công cụ hệ thống"])

with tab_upload:
    st.subheader("Kiểm tra nhanh file CSV")
    expected_type = st.selectbox(
        "Loại dữ liệu",
        [
            "custom",
            "rfm_upload",
            "orders_base_final_minimal",
            "ratings_df_minimal",
            "transactions_df_minimal",
            "regression_input_schema",
        ],
    )

    uploaded = st.file_uploader("Tải lên file CSV", type=["csv"])
    if uploaded is not None:
        raw = uploaded.getvalue()
        checksum = hashlib.md5(raw).hexdigest()
        df = pd.read_csv(uploaded)

        st.write(f"**MD5:** `{checksum}`")
        st.write(f"**Kích thước:** {df.shape[0]:,} dòng × {df.shape[1]:,} cột")
        st.dataframe(df.head(20), use_container_width=True, hide_index=True)

        feature_columns = (
            regression_schema.get("feature_columns", [])
            if expected_type == "regression_input_schema" and isinstance(regression_schema, dict)
            else []
        )
        report = validate_csv_contract(df, expected_type, feature_columns=feature_columns)
        if report["ok"]:
            st.success("File hợp lệ.")
        else:
            st.error("File chưa hợp lệ.")
        st.json(report, expanded=False)

with tab_tools:
    st.subheader("Bảo trì")
    if st.button("Làm mới bộ nhớ đệm", type="primary", use_container_width=True):
        clear_loader_caches()
        st.success("Đã làm mới bộ nhớ đệm.")
    st.info("Dùng trang này khi dữ liệu vừa được cập nhật hoặc sau khi xuất thêm artifact mới.")

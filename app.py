from __future__ import annotations

import streamlit as st

from utils.loaders import load_processed_table, load_summary_json


st.set_page_config(
    page_title="Olist Customer Insights",
    page_icon="🛍️",
    layout="wide",
)

st.title("🛍️ Olist Customer Insights")
st.caption(
    "Nền tảng hỗ trợ theo dõi đơn hàng, phân khúc khách hàng, gợi ý sản phẩm,"
    " mua kèm và dự đoán nhanh cho hoạt động bán hàng."
)


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


orders_df = load_processed_table("orders_base_final")
rfm_df = load_processed_table("rfm_df")
fpgrowth_summary = load_summary_json("fpgrowth_final_summary.json")
clustering_summary = load_summary_json("clustering_final_summary.json")

orders_count = len(orders_df) if orders_df is not None else None
customer_count = (
    orders_df["customer_unique_id"].nunique()
    if orders_df is not None and "customer_unique_id" in orders_df.columns
    else None
)
avg_review = (
    orders_df["review_score"].astype(float).mean()
    if orders_df is not None and "review_score" in orders_df.columns
    else None
)
avg_order_value = (
    orders_df["payment_value_sum"].astype(float).mean()
    if orders_df is not None and "payment_value_sum" in orders_df.columns
    else None
)
segment_count = None
if isinstance(clustering_summary, dict):
    segment_count = clustering_summary.get("kmeans_final_k")
rules_count = None
if isinstance(fpgrowth_summary, dict):
    rules_count = fpgrowth_summary.get("n_rules_usable_for_ui")

hero_left, hero_right = st.columns([1.8, 1])
with hero_left:
    st.markdown(
        """
### Hệ thống hỗ trợ quyết định cho bán hàng và chăm sóc khách hàng
- Theo dõi xu hướng doanh thu, đánh giá và trạng thái đơn hàng.
- Phân nhóm khách hàng theo hành vi mua sắm để xây chiến lược chăm sóc.
- Gợi ý sản phẩm cho khách hàng hiện hữu, khách hàng mới và theo sản phẩm tương tự.
- Khai thác các nhóm sản phẩm thường được mua kèm để tăng giá trị đơn hàng.
- Dự đoán nhanh cho các tình huống vận hành thường gặp.
"""
    )
with hero_right:
    with st.container(border=True):
        st.markdown("### Chỉ số nhanh")
        st.write(f"**Đơn hàng:** {fmt(orders_count, 'int')}")
        st.write(f"**Khách hàng:** {fmt(customer_count, 'int')}")
        st.write(f"**Điểm đánh giá TB:** {fmt(avg_review, 'float2')}")
        st.write(f"**Giá trị đơn hàng TB:** {fmt(avg_order_value, 'float2')}")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Đơn hàng", fmt(orders_count, "int"))
k2.metric("Khách hàng", fmt(customer_count, "int"))
k3.metric("Nhóm khách hàng", fmt(segment_count, "int"))
k4.metric("Luật mua kèm", fmt(rules_count, "int"))

st.subheader("Bắt đầu sử dụng")
step1, step2, step3 = st.columns(3)
with step1:
    with st.container(border=True):
        st.markdown("### 1. Xem tổng quan")
        st.write("Mở Dashboard để theo dõi đơn hàng, đánh giá, danh mục và xu hướng mua sắm.")
with step2:
    with st.container(border=True):
        st.markdown("### 2. Phân tích khách hàng")
        st.write("Dùng Segmentation và Recommendation để hiểu khách hàng và gợi ý sản phẩm phù hợp.")
with step3:
    with st.container(border=True):
        st.markdown("### 3. Hỗ trợ ra quyết định")
        st.write("Dùng Mua kèm và Dự đoán để tối ưu bán chéo, chăm sóc và vận hành hằng ngày.")

st.subheader("Các tính năng chính")
modules = [
    ("📊 Dashboard", "Theo dõi số liệu vận hành, đơn hàng, đánh giá và xu hướng."),
    ("👥 Phân khúc khách hàng", "Nhận diện nhóm khách hàng để ưu tiên giữ chân hoặc tái kích hoạt."),
    ("🎯 Khuyến nghị sản phẩm", "Gợi ý top sản phẩm cho khách hàng hoặc sản phẩm tương tự."),
    ("🧺 Mua kèm thông minh", "Tìm các nhóm sản phẩm nên bán cùng nhau để tăng giá trị đơn hàng."),
    ("🔮 Dự đoán", "Ước tính nhanh kết quả hoặc phân tích nội dung đánh giá."),
    ("⚙️ Trung tâm vận hành", "Dành cho người phụ trách hệ thống khi cần kiểm tra và làm mới dữ liệu."),
]
cols = st.columns(3)
for idx, (title, desc) in enumerate(modules):
    with cols[idx % 3]:
        with st.container(border=True):
            st.markdown(f"### {title}")
            st.write(desc)

st.info("Chọn một trang ở thanh điều hướng bên trái để bắt đầu.")

from __future__ import annotations

import streamlit as st

from utils.inference import predict_payment_value, predict_review_tabular, predict_review_text
from utils.loaders import load_model_json, load_summary_json


st.title("🔮 Dự đoán & phân tích")
st.caption("Phân tích nhanh đánh giá đơn hàng, nội dung bình luận và giá trị đơn hàng dự kiến.")


def fmt(value, kind: str = "text", default: str = "—") -> str:
    if value is None:
        return default
    try:
        if kind == "float4":
            return f"{float(value):.4f}"
        if kind == "float2":
            return f"{float(value):.2f}"
        return str(value)
    except Exception:
        return default


def default_value_for_feature(feature_name: str):
    defaults = {
        "item_count": 1.0,
        "unique_products": 1.0,
        "unique_sellers": 1.0,
        "price_sum": 100.0,
        "freight_value_sum": 15.0,
        "price_mean": 100.0,
        "payment_value_sum": 115.0,
        "payment_installments_max": 1.0,
        "basket_value": 115.0,
        "purchase_year": 2018,
        "purchase_month": 6,
        "purchase_day": 15,
        "purchase_hour": 12,
        "purchase_dayofweek": 2,
        "customer_state": "SP",
        "main_category": "bed_bath_table",
        "payment_type_mode": "credit_card",
    }
    return defaults.get(feature_name, "")


FEATURE_LABELS = {
    "item_count": "Số lượng sản phẩm",
    "unique_products": "Số sản phẩm khác nhau",
    "unique_sellers": "Số nhà bán hàng",
    "price_sum": "Tổng giá trị sản phẩm",
    "freight_value_sum": "Tổng phí vận chuyển",
    "price_mean": "Giá trung bình sản phẩm",
    "payment_value_sum": "Tổng giá trị thanh toán",
    "payment_installments_max": "Số kỳ thanh toán cao nhất",
    "basket_value": "Giá trị giỏ hàng",
    "purchase_year": "Năm mua",
    "purchase_month": "Tháng mua",
    "purchase_day": "Ngày mua",
    "purchase_hour": "Giờ mua",
    "purchase_dayofweek": "Thứ trong tuần",
    "customer_state": "Khu vực khách hàng",
    "main_category": "Danh mục chính",
    "payment_type_mode": "Hình thức thanh toán",
}


def input_widget(feature: str, prefix: str):
    label = FEATURE_LABELS.get(feature, feature)
    default = default_value_for_feature(feature)
    if feature in {"purchase_year", "purchase_month", "purchase_day", "purchase_hour", "purchase_dayofweek"}:
        min_val, max_val = 0, 2030
        if feature == "purchase_year":
            min_val, max_val = 2016, 2030
        elif feature == "purchase_month":
            min_val, max_val = 1, 12
        elif feature == "purchase_day":
            min_val, max_val = 1, 31
        elif feature == "purchase_hour":
            min_val, max_val = 0, 23
        elif feature == "purchase_dayofweek":
            min_val, max_val = 0, 6
        return st.number_input(label, min_value=min_val, max_value=max_val, value=int(default), key=f"{prefix}_{feature}")
    if isinstance(default, (int, float)):
        return st.number_input(label, min_value=0.0, value=float(default), key=f"{prefix}_{feature}")
    return st.text_input(label, value=str(default), key=f"{prefix}_{feature}")


def render_feature_form(numeric_features: list[str], categorical_features: list[str], prefix: str) -> dict:
    values: dict = {}
    if numeric_features:
        st.markdown("#### Thông tin định lượng")
        cols = st.columns(3)
        for idx, feature in enumerate(numeric_features):
            with cols[idx % 3]:
                values[feature] = input_widget(feature, prefix)
    if categorical_features:
        st.markdown("#### Thông tin phân loại")
        cols = st.columns(3)
        for idx, feature in enumerate(categorical_features):
            with cols[idx % 3]:
                values[feature] = input_widget(feature, prefix)
    return values


classification_summary = load_summary_json("classification_final_summary.json")
regression_summary = load_summary_json("regression_final_summary.json")
regression_schema = load_model_json("regression_input_schema.json")

tab1, tab2, tab3 = st.tabs(["Đánh giá đơn hàng", "Phân tích bình luận", "Ước tính giá trị đơn hàng"])

with tab1:
    st.subheader("Dự đoán đánh giá tích cực hay tiêu cực")
    cls_numeric = classification_summary.get("numeric_features", []) if isinstance(classification_summary, dict) else []
    cls_categorical = classification_summary.get("categorical_features", []) if isinstance(classification_summary, dict) else []
    if not cls_numeric and not cls_categorical:
        cls_numeric = [
            "item_count", "unique_products", "unique_sellers", "price_sum", "freight_value_sum",
            "price_mean", "payment_value_sum", "payment_installments_max", "basket_value",
            "purchase_year", "purchase_month", "purchase_day", "purchase_hour", "purchase_dayofweek",
        ]
        cls_categorical = ["customer_state", "main_category", "payment_type_mode"]

    cls_input = render_feature_form(cls_numeric, cls_categorical, prefix="cls")
    if st.button("Phân tích đánh giá", type="primary", use_container_width=True):
        result = predict_review_tabular(cls_input)
        if result["ok"]:
            left, right = st.columns([1, 1.2])
            with left:
                st.success(f"Kết quả: {result['label_text']}")
                if result.get("confidence") is not None:
                    st.write(f"Độ tin cậy: **{fmt(result['confidence'], 'float4')}**")
            with right:
                if "class_probabilities" in result:
                    st.json(result["class_probabilities"], expanded=False)
        else:
            st.error(result["message"])

with tab2:
    st.subheader("Phân tích cảm xúc từ nội dung bình luận")
    quick_examples = st.columns(3)
    if quick_examples[0].button("Ví dụ tích cực", use_container_width=True):
        st.session_state["prediction_text_example"] = "produto excelente chegou rápido e bem embalado"
    if quick_examples[1].button("Ví dụ tiêu cực", use_container_width=True):
        st.session_state["prediction_text_example"] = "produto ruim chegou com defeito e atraso"
    if quick_examples[2].button("Xóa nội dung", use_container_width=True):
        st.session_state["prediction_text_example"] = ""

    review_text = st.text_area(
        "Nội dung bình luận",
        height=160,
        value=st.session_state.get("prediction_text_example", "produto excelente chegou rápido e bem embalado"),
    )

    if st.button("Phân tích cảm xúc", type="primary", use_container_width=True):
        result = predict_review_text(review_text)
        if result["ok"]:
            st.success(f"Kết quả: {result['label_text']}")
            if result.get("score") is not None:
                st.write(f"Điểm phân tích: **{fmt(result['score'], 'float4')}**")
        else:
            st.error(result["message"])

with tab3:
    st.subheader("Ước tính giá trị đơn hàng")
    reg_numeric = regression_schema.get("numeric_features", []) if isinstance(regression_schema, dict) else []
    reg_categorical = regression_schema.get("categorical_features", []) if isinstance(regression_schema, dict) else []
    if not reg_numeric and isinstance(regression_summary, dict):
        reg_numeric = regression_summary.get("numeric_features", [])
        reg_categorical = regression_summary.get("categorical_features", [])

    reg_input = render_feature_form(reg_numeric, reg_categorical, prefix="reg")
    if st.button("Ước tính giá trị", type="primary", use_container_width=True):
        result = predict_payment_value(reg_input)
        if result["ok"]:
            st.success(f"Giá trị đơn hàng dự kiến: {fmt(result['prediction'], 'float2')}")
        else:
            st.error(result["message"])

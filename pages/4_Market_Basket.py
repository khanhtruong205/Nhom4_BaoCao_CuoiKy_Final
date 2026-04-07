from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.inference import get_association_rules
from utils.loaders import load_metric_csv


st.title("🧺 Mua kèm thông minh")
st.caption("Khám phá các nhóm sản phẩm thường xuất hiện cùng nhau để hỗ trợ bán chéo và tối ưu giỏ hàng.")


def fmt(value, kind: str = "text", default: str = "—") -> str:
    if value is None:
        return default
    try:
        if kind == "int":
            return f"{int(value):,}"
        if kind == "float4":
            return f"{float(value):.4f}"
        if kind == "float2":
            return f"{float(value):.2f}"
        return str(value)
    except Exception:
        return default


itemsets_df = load_metric_csv("frequent_itemsets.csv")

preset = st.radio(
    "Mức gợi ý",
    ["Cân bằng", "Mạnh hơn", "Mở rộng"],
    horizontal=True,
)
if preset == "Cân bằng":
    default_support, default_conf, default_lift = 0.001, 0.10, 1.2
elif preset == "Mạnh hơn":
    default_support, default_conf, default_lift = 0.003, 0.20, 1.5
else:
    default_support, default_conf, default_lift = 0.001, 0.05, 1.0

c1, c2, c3 = st.columns(3)
min_support = c1.slider("Tần suất xuất hiện tối thiểu", 0.0, 0.05, float(default_support), 0.001, format="%.3f")
min_conf = c2.slider("Độ tin cậy tối thiểu", 0.0, 1.0, float(default_conf), 0.01)
min_lift = c3.slider("Mức liên kết tối thiểu", 0.0, 10.0, float(default_lift), 0.1)
hide_unknown = st.checkbox("Ẩn giá trị không xác định", value=True)
top_n = st.slider("Số luật hiển thị", 10, 100, 30, 10)

with st.expander("Ý nghĩa 3 chỉ số", expanded=False):
    st.write("- Tần suất xuất hiện: mức độ một nhóm mua kèm xuất hiện trong toàn bộ giao dịch.")
    st.write("- Độ tin cậy: xác suất vế phải xuất hiện khi vế trái đã có trong giỏ hàng.")
    st.write("- Mức liên kết: độ mạnh của mối quan hệ so với ngẫu nhiên.")

result = get_association_rules(
    min_support=min_support,
    min_confidence=min_conf,
    min_lift=min_lift,
    hide_unknown=hide_unknown,
    top_n=top_n,
)

tab_rules, tab_itemsets = st.tabs(["Luật mua kèm", "Nhóm sản phẩm phổ biến"])

with tab_rules:
    if result["ok"]:
        rules_df = result["data"]
        if rules_df is not None and not rules_df.empty:
            b1, b2, b3 = st.columns(3)
            b1.metric("Số luật", len(rules_df))
            b2.metric("Mức lọc", preset)
            b3.metric("Ẩn dữ liệu rỗng", "Có" if hide_unknown else "Không")

            preferred_cols = [
                "rule_str",
                "antecedents_str",
                "consequents_str",
                "lift",
                "confidence",
                "support",
                "support_count",
            ]
            preferred_cols = [c for c in preferred_cols if c in rules_df.columns] + [c for c in rules_df.columns if c not in preferred_cols]
            st.dataframe(rules_df[preferred_cols], use_container_width=True, hide_index=True)

            left, right = st.columns(2)
            with left:
                if {"rule_str", "lift"}.issubset(rules_df.columns):
                    plot_df = rules_df.head(10).copy()
                    fig = px.bar(plot_df, x="lift", y="rule_str", orientation="h", title="Top luật theo mức liên kết")
                    fig.update_layout(yaxis={"categoryorder": "total ascending"})
                    st.plotly_chart(fig, use_container_width=True)
            with right:
                if {"rule_str", "confidence"}.issubset(rules_df.columns):
                    plot_df = rules_df.head(10).copy()
                    fig = px.bar(plot_df, x="confidence", y="rule_str", orientation="h", title="Top luật theo độ tin cậy")
                    fig.update_layout(yaxis={"categoryorder": "total ascending"})
                    st.plotly_chart(fig, use_container_width=True)

            top_rule = rules_df.iloc[0]
            st.success(
                f"Gợi ý nổi bật: {top_rule.get('rule_str', '—')} | "
                f"tần suất={fmt(top_rule.get('support'), 'float4')}, "
                f"độ tin cậy={fmt(top_rule.get('confidence'), 'float4')}, "
                f"mức liên kết={fmt(top_rule.get('lift'), 'float4')}."
            )
        else:
            st.info("Không có luật phù hợp với bộ lọc hiện tại.")
    else:
        st.error(result["message"])

with tab_itemsets:
    if itemsets_df is not None and not itemsets_df.empty:
        work = itemsets_df.copy()
        if "support" in work.columns:
            work["support"] = pd.to_numeric(work["support"], errors="coerce")
            work = work[work["support"] >= min_support]
        if hide_unknown and "itemsets_str" in work.columns:
            work = work[~work["itemsets_str"].astype(str).str.contains(r"\bunknown\b", case=False, na=False)]
        sort_cols = [col for col in ["support", "itemset_size"] if col in work.columns]
        if sort_cols:
            work = work.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        st.dataframe(work.head(30), use_container_width=True, hide_index=True)
        if {"itemsets_str", "support"}.issubset(work.columns):
            plot_df = work.head(10).copy()
            fig = px.bar(plot_df, x="support", y="itemsets_str", orientation="h", title="Top nhóm sản phẩm theo tần suất")
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Hiện chưa có dữ liệu nhóm sản phẩm phổ biến.")

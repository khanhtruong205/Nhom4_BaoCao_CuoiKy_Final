from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.inference import recommend_for_user, recommend_similar_products


st.title("🎯 Khuyến nghị sản phẩm")
st.caption("Gợi ý sản phẩm phù hợp cho khách hàng và tìm sản phẩm tương tự để hỗ trợ bán chéo.")


def source_label(mode: str | None) -> str:
    mapping = {
        "collaborative_filtering": "Dựa trên hành vi mua sắm tương tự",
        "cold_start_popularity": "Dựa trên sản phẩm phổ biến cho khách mới",
        "preview_collaborative": "Dữ liệu minh họa cho khách hàng hiện hữu",
        "preview_cold_start": "Dữ liệu minh họa cho khách hàng mới",
        "neighbors": "Dựa trên độ tương đồng sản phẩm",
        "fallback_neighbors_preview": "Dữ liệu minh họa cho sản phẩm tương tự",
        "preview_neighbors": "Dữ liệu minh họa cho sản phẩm tương tự",
        "preview_unknown_item_fallback": "Dữ liệu minh họa cho sản phẩm chưa có lịch sử",
    }
    return mapping.get(str(mode), "Nguồn gợi ý chưa xác định")


def to_dataframe(rows: list[dict] | pd.DataFrame | None) -> pd.DataFrame:
    if rows is None:
        return pd.DataFrame()
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    if isinstance(rows, list):
        return pd.DataFrame(rows)
    return pd.DataFrame()


def prepare_reco_display(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    work = df.copy()
    rename_map = {
        "product_id": "Mã sản phẩm",
        "product_category_name_english": "Danh mục",
        "estimated_score": "Điểm gợi ý",
        "weighted_rating": "Đánh giá trọng số",
        "avg_price": "Giá trung bình",
        "purchase_count": "Số lượt mua",
        "rating_mean": "Điểm đánh giá TB",
        "rating_count": "Số lượt đánh giá",
        "neighbor_rank": "Thứ hạng tương tự",
        "reason": "Nguồn gợi ý",
    }
    work = work.rename(columns=rename_map)
    preferred = [
        "Mã sản phẩm",
        "Danh mục",
        "Điểm gợi ý",
        "Đánh giá trọng số",
        "Giá trung bình",
        "Số lượt mua",
        "Điểm đánh giá TB",
        "Số lượt đánh giá",
        "Thứ hạng tương tự",
        "Nguồn gợi ý",
    ]
    ordered = [c for c in preferred if c in work.columns] + [c for c in work.columns if c not in preferred]
    return work[ordered]


tab_user, tab_product, tab_help = st.tabs(["Theo khách hàng", "Theo sản phẩm", "Hướng dẫn sử dụng"])

with tab_user:
    st.subheader("Gợi ý cho một khách hàng")
    c1, c2 = st.columns([2, 1])
    with c1:
        customer_id = st.text_input("Mã khách hàng", value="")
    with c2:
        top_n = st.slider("Số lượng gợi ý", 5, 20, 10, 1)

    if st.button("Lấy gợi ý", type="primary", use_container_width=True):
        result = recommend_for_user(customer_id=customer_id, top_n=top_n)
        if result["ok"]:
            reco_df = prepare_reco_display(to_dataframe(result.get("data")))
            if reco_df.empty:
                st.info("Chưa có sản phẩm phù hợp để hiển thị.")
            else:
                a1, a2 = st.columns([1, 2])
                with a1:
                    st.success("Đã tạo danh sách gợi ý.")
                    st.write(f"**Cách gợi ý:** {source_label(result.get('mode'))}")
                    st.write(f"**Loại khách hàng:** {'Khách hàng hiện hữu' if result.get('known_user') else 'Khách hàng mới'}")
                    if result.get("message"):
                        st.caption(result["message"])
                with a2:
                    st.dataframe(reco_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "Tải danh sách gợi ý",
                    data=reco_df.to_csv(index=False).encode("utf-8"),
                    file_name="product_recommendations.csv",
                    mime="text/csv",
                )
        else:
            st.error(result["message"])

with tab_product:
    st.subheader("Tìm sản phẩm tương tự")
    c1, c2 = st.columns([2, 1])
    with c1:
        product_id = st.text_input("Mã sản phẩm", value="")
    with c2:
        top_n_neighbors = st.slider("Số sản phẩm tương tự", 5, 20, 10, 1)

    if st.button("Tìm sản phẩm", type="primary", use_container_width=True):
        result = recommend_similar_products(product_id=product_id, top_n=top_n_neighbors)
        if result["ok"]:
            neighbor_df = prepare_reco_display(to_dataframe(result.get("data")))
            if neighbor_df.empty:
                st.info("Chưa tìm thấy sản phẩm tương tự.")
            else:
                st.success("Đã tạo danh sách sản phẩm tương tự.")
                st.write(f"**Cách gợi ý:** {source_label(result.get('mode'))}")
                if result.get("message"):
                    st.caption(result["message"])
                st.dataframe(neighbor_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "Tải danh sách sản phẩm tương tự",
                    data=neighbor_df.to_csv(index=False).encode("utf-8"),
                    file_name="similar_products.csv",
                    mime="text/csv",
                )
        else:
            st.error(result["message"])

with tab_help:
    st.subheader("Khi nào nên dùng từng loại gợi ý")
    help_rows = [
        {
            "Tình huống": "Muốn gợi ý cho khách hàng có lịch sử mua sắm",
            "Nên dùng": "Theo khách hàng",
            "Giá trị": "Gợi ý gần với sở thích và hành vi mua trước đó.",
        },
        {
            "Tình huống": "Khách hàng mới chưa có lịch sử",
            "Nên dùng": "Theo khách hàng",
            "Giá trị": "Hệ thống ưu tiên các sản phẩm đang phổ biến và dễ quan tâm.",
        },
        {
            "Tình huống": "Muốn bán chéo hoặc thay thế sản phẩm",
            "Nên dùng": "Theo sản phẩm",
            "Giá trị": "Gợi ý các mặt hàng có mức độ tương đồng cao.",
        },
    ]
    st.dataframe(pd.DataFrame(help_rows), use_container_width=True, hide_index=True)

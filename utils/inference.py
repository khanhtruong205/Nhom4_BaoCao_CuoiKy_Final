from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from utils.loaders import (
    load_data_artifact_csv,
    load_integration_payload,
    load_joblib_model,
    load_metric_csv,
    load_model_json,
    load_pickle_model,
    load_prediction_csv,
    load_processed_table,
    load_summary_json,
)


# =========================================================
# Generic helpers
# =========================================================
def _positive_negative_label(pred: int | float | str) -> str:
    try:
        return "Positive" if int(pred) == 1 else "Negative"
    except Exception:
        return str(pred)


def _first_not_none(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _records_from_preview_block(block: dict[str, Any] | None, top_n: int = 10) -> list[dict[str, Any]]:
    if not isinstance(block, dict):
        return []
    rows = block.get("top_5", [])
    if isinstance(rows, list):
        return rows[:top_n]
    return []


def _load_product_lookup() -> pd.DataFrame | None:
    lookup = _first_not_none(
        load_data_artifact_csv("product_lookup.csv"),
        load_data_artifact_csv("product_lookup"),
        load_processed_table("product_lookup"),
    )
    if lookup is None or lookup.empty:
        return None

    if "product_id" in lookup.columns:
        lookup["product_id"] = lookup["product_id"].astype(str)

    return lookup


def _merge_product_metadata(df: pd.DataFrame | None) -> pd.DataFrame | None:
    if df is None or df.empty or "product_id" not in df.columns:
        return df

    lookup = _load_product_lookup()
    if lookup is None or "product_id" not in lookup.columns:
        return df

    useful_cols = [
        "product_id",
        "product_category_name_english",
        "main_category",
        "avg_price",
        "purchase_count",
        "rating_mean",
        "rating_count",
        "weighted_rating",
    ]
    useful_cols = [col for col in useful_cols if col in lookup.columns]

    if len(useful_cols) <= 1:
        return df

    merged = df.copy()
    merged["product_id"] = merged["product_id"].astype(str)
    merged = merged.merge(
        lookup[useful_cols].drop_duplicates(subset=["product_id"]),
        on="product_id",
        how="left",
        suffixes=("", "_lookup"),
    )
    return merged


def _preview_payload() -> dict[str, Any]:
    payload = load_integration_payload()
    return payload if isinstance(payload, dict) else {}


def _normalize_probability_output(probabilities: list[float] | np.ndarray) -> tuple[dict[str, float], float]:
    probs = [float(x) for x in probabilities]
    mapping = {str(i): float(p) for i, p in enumerate(probs)}
    confidence = max(probs) if probs else None
    return mapping, float(confidence) if confidence is not None else None


# =========================================================
# Prediction helpers
# =========================================================
def predict_review_tabular(input_dict: dict[str, Any]) -> dict[str, Any]:
    model = load_joblib_model("best_classifier_baseline.joblib")
    payload = _preview_payload()

    if model is None:
        preview = payload.get("classification_tabular")
        if isinstance(preview, dict):
            pred = int(preview.get("predicted_label", 1))
            probabilities = preview.get("class_probabilities", {})
            confidence = preview.get("confidence")
            return {
                "ok": True,
                "mode": "preview",
                "prediction": pred,
                "label_text": _positive_negative_label(pred),
                "confidence": float(confidence) if confidence is not None else None,
                "class_probabilities": probabilities,
                "message": "Đang dùng preview payload vì thiếu model classification.",
            }
        return {"ok": False, "message": "Thiếu file best_classifier_baseline.joblib và không có preview payload."}

    try:
        X = pd.DataFrame([input_dict])
        pred = model.predict(X)[0]

        result: dict[str, Any] = {
            "ok": True,
            "mode": "model",
            "prediction": int(pred),
            "label_text": _positive_negative_label(pred),
        }

        if hasattr(model, "predict_proba"):
            try:
                probs = model.predict_proba(X)[0]
                prob_map, confidence = _normalize_probability_output(probs)
                result["class_probabilities"] = prob_map
                result["confidence"] = confidence
            except Exception:
                pass

        return result
    except Exception as exc:
        return {"ok": False, "message": f"Lỗi classification inference: {exc}"}


def predict_review_text(text: str) -> dict[str, Any]:
    model = load_joblib_model("best_classifier_text_tfidf.joblib")
    payload = _preview_payload()

    if model is None:
        preview_rows = payload.get("classification_text", [])
        if isinstance(preview_rows, list) and preview_rows:
            normalized = str(text or "").strip().lower()
            chosen = None

            if normalized == "":
                for row in preview_rows:
                    if str(row.get("text", "")).strip() == "":
                        chosen = row
                        break

            if chosen is None:
                negative_keywords = ["atras", "defeito", "ruim", "problema", "péssimo", "horrível"]
                if any(keyword in normalized for keyword in negative_keywords):
                    chosen = next((row for row in preview_rows if int(row.get("predicted_label", 1)) == 0), None)

            if chosen is None:
                chosen = preview_rows[0]

            pred = int(chosen.get("predicted_label", 1))
            return {
                "ok": True,
                "mode": "preview",
                "prediction": pred,
                "label_text": _positive_negative_label(pred),
                "score": float(chosen.get("raw_score")) if chosen.get("raw_score") is not None else None,
                "message": "Đang dùng preview payload vì thiếu model text classification.",
            }

        return {"ok": False, "message": "Thiếu file best_classifier_text_tfidf.joblib và không có preview payload."}

    try:
        pred = model.predict([text])[0]
        result: dict[str, Any] = {
            "ok": True,
            "mode": "model",
            "prediction": int(pred),
            "label_text": _positive_negative_label(pred),
        }

        if hasattr(model, "decision_function"):
            try:
                result["score"] = float(np.ravel(model.decision_function([text]))[0])
            except Exception:
                pass

        return result
    except Exception as exc:
        return {"ok": False, "message": f"Lỗi text classification inference: {exc}"}


def predict_payment_value(input_dict: dict[str, Any]) -> dict[str, Any]:
    model = load_joblib_model("best_regressor_baseline.joblib")
    payload = _preview_payload()

    if model is None:
        preview = payload.get("regression")
        if isinstance(preview, dict):
            prediction = preview.get("predicted_payment_value_sum")
            return {
                "ok": True,
                "mode": "preview",
                "prediction": float(prediction) if prediction is not None else None,
                "reference_value": preview.get("y_true_reference"),
                "absolute_error_vs_reference": preview.get("absolute_error_vs_reference"),
                "message": "Đang dùng preview payload vì thiếu model regression.",
            }
        return {"ok": False, "message": "Thiếu file best_regressor_baseline.joblib và không có preview payload."}

    try:
        X = pd.DataFrame([input_dict])
        pred = model.predict(X)[0]
        return {"ok": True, "mode": "model", "prediction": float(pred)}
    except Exception as exc:
        return {"ok": False, "message": f"Lỗi regression inference: {exc}"}


# =========================================================
# Clustering helpers
# =========================================================
def _segment_name_from_preview(cluster: int | None) -> str | None:
    payload = _preview_payload()
    clustering_block = payload.get("clustering", {})
    edge_block = payload.get("clustering_edge_case", {})

    if isinstance(clustering_block, dict) and clustering_block.get("assigned_cluster") == cluster:
        return clustering_block.get("segment_name")

    if isinstance(edge_block, dict) and edge_block.get("assigned_cluster") == cluster:
        return edge_block.get("segment_name")

    return None


def predict_customer_cluster(
    customer_id: str | None = None,
    rfm_row: dict[str, Any] | None = None,
    model_type: str = "kmeans",
) -> dict[str, Any]:
    payload = _preview_payload()
    summary = load_summary_json("clustering_final_summary.json")

    rfm_df = load_processed_table("rfm_df")
    scaler = load_joblib_model("rfm_standard_scaler.joblib")
    model_filename = "kmeans_model.joblib" if model_type == "kmeans" else "gmm_model.joblib"
    model = load_joblib_model(model_filename)

    features = ["recency_days", "frequency_orders", "monetary_value"]

    if rfm_df is not None and model is not None and scaler is not None:
        try:
            if rfm_row is None:
                if customer_id is None:
                    return {"ok": False, "message": "Cần customer_id hoặc rfm_row."}
                work = rfm_df[rfm_df["customer_unique_id"].astype(str) == str(customer_id)]
                if work.empty:
                    preview = payload.get("clustering")
                    if isinstance(preview, dict):
                        return {
                            "ok": True,
                            "mode": "preview",
                            "cluster": int(preview.get("assigned_cluster", 0)),
                            "segment_name": preview.get("segment_name"),
                            "rfm": {
                                "recency_days": None,
                                "frequency_orders": None,
                                "monetary_value": None,
                            },
                            "message": "Không tìm thấy customer trong rfm_df. Đang dùng preview payload.",
                        }
                    return {"ok": False, "message": "Không tìm thấy customer_unique_id trong rfm_df."}
                row = work.iloc[0][features].to_dict()
            else:
                row = {k: float(rfm_row[k]) for k in features}

            X = pd.DataFrame([row])
            X_model = np.log1p(X)
            X_scaled = scaler.transform(X_model)
            label = model.predict(X_scaled)[0]
            label = int(label)

            return {
                "ok": True,
                "mode": "model",
                "cluster": label,
                "segment_name": _segment_name_from_preview(label),
                "rfm": row,
                "model_type": model_type,
                "selection_note": summary.get("kmeans_selection_reason") if isinstance(summary, dict) else None,
            }
        except Exception as exc:
            return {"ok": False, "message": f"Lỗi clustering inference: {exc}"}

    preview = payload.get("clustering")
    if isinstance(preview, dict):
        return {
            "ok": True,
            "mode": "preview",
            "cluster": int(preview.get("assigned_cluster", 0)),
            "segment_name": preview.get("segment_name"),
            "rfm": {
                "recency_days": rfm_row.get("recency_days") if isinstance(rfm_row, dict) else None,
                "frequency_orders": rfm_row.get("frequency_orders") if isinstance(rfm_row, dict) else None,
                "monetary_value": rfm_row.get("monetary_value") if isinstance(rfm_row, dict) else None,
            },
            "model_type": model_type,
            "selection_note": summary.get("kmeans_selection_reason") if isinstance(summary, dict) else None,
            "message": "Đang dùng preview payload vì thiếu artifact clustering.",
        }

    return {"ok": False, "message": f"Thiếu artifact clustering ({model_filename}, rfm_df hoặc scaler)."}


# =========================================================
# Recommendation helpers
# =========================================================
def recommend_for_user(customer_id: str, top_n: int = 10) -> dict[str, Any]:
    customer_id = str(customer_id).strip()
    payload = _preview_payload()

    best_model = load_pickle_model("best_surprise_model.pkl")
    bundle = load_pickle_model("surprise_deployment_bundle.pkl")
    seen_map = load_pickle_model("seen_items_map.pkl")

    ratings_df = load_processed_table("ratings_df")
    known_users_artifact = load_data_artifact_csv("known_users.csv")
    candidate_items_df = _first_not_none(
        load_data_artifact_csv("candidate_items.csv"),
        load_prediction_csv("popular_products_fallback.csv"),
    )

    def _preview_known_user() -> dict[str, Any]:
        block = payload.get("recommendation_known_user", {})
        rows = _records_from_preview_block(block, top_n=top_n)
        return {
            "ok": True,
            "mode": "preview_collaborative",
            "data": rows,
            "known_user": True,
            "message": "Đang dùng preview payload cho known user recommendation.",
        }

    def _preview_unknown_user() -> dict[str, Any]:
        block = payload.get("recommendation_unknown_user", {})
        rows = _records_from_preview_block(block, top_n=top_n)
        return {
            "ok": True,
            "mode": "preview_cold_start",
            "data": rows,
            "known_user": False,
            "message": "Đang dùng preview payload cho cold-start recommendation.",
        }

    if not customer_id:
        return {"ok": False, "message": "Vui lòng nhập customer_unique_id."}

    if best_model is None or bundle is None or seen_map is None or candidate_items_df is None:
        preview_known_id = payload.get("recommendation_known_user", {}).get("customer_unique_id")
        if customer_id == str(preview_known_id):
            return _preview_known_user()
        return _preview_unknown_user()

    try:
        candidate_items_df = candidate_items_df.copy()
        candidate_items_df["product_id"] = candidate_items_df["product_id"].astype(str)

        known_users: set[str] = set()
        if ratings_df is not None and "customer_unique_id" in ratings_df.columns:
            known_users = set(ratings_df["customer_unique_id"].astype(str).unique())
        elif known_users_artifact is not None and "customer_unique_id" in known_users_artifact.columns:
            known_users = set(known_users_artifact["customer_unique_id"].astype(str).unique())

        all_item_ids = candidate_items_df["product_id"].astype(str).tolist()

        if customer_id not in known_users:
            fallback = candidate_items_df.head(top_n).copy()
            fallback["reason"] = fallback.get("reason", "cold_start_popularity")
            fallback = _merge_product_metadata(fallback)
            return {
                "ok": True,
                "mode": "cold_start_popularity",
                "data": fallback.to_dict(orient="records"),
                "known_user": False,
            }

        seen_items = seen_map.get(customer_id, set())
        seen_items = {str(x) for x in seen_items}
        candidates = [iid for iid in all_item_ids if iid not in seen_items]

        rows: list[dict[str, Any]] = []
        for iid in candidates[:750]:
            try:
                est = best_model.predict(customer_id, iid).est
                rows.append(
                    {
                        "product_id": iid,
                        "estimated_score": float(est),
                        "reason": "collaborative_filtering",
                    }
                )
            except Exception:
                continue

        reco_df = pd.DataFrame(rows)
        if reco_df.empty:
            return _preview_known_user()

        reco_df = reco_df.sort_values("estimated_score", ascending=False).head(top_n)
        reco_df = _merge_product_metadata(reco_df)

        return {
            "ok": True,
            "mode": "collaborative_filtering",
            "data": reco_df.to_dict(orient="records"),
            "known_user": True,
        }
    except Exception as exc:
        return {"ok": False, "message": f"Lỗi recommendation inference: {exc}"}


def recommend_similar_products(product_id: str, top_n: int = 10) -> dict[str, Any]:
    product_id = str(product_id).strip()
    payload = _preview_payload()

    model = load_pickle_model("item_knn_neighbors_model.pkl")
    fallback = load_prediction_csv("sample_product_neighbors.csv")

    def _preview_known_product() -> dict[str, Any]:
        block = payload.get("recommendation_known_product_neighbors", {})
        rows = _records_from_preview_block(block, top_n=top_n)
        return {
            "ok": True,
            "mode": "preview_neighbors",
            "data": rows,
            "message": "Đang dùng preview payload cho similar product.",
        }

    def _preview_unknown_product() -> dict[str, Any]:
        block = payload.get("recommendation_unknown_product_neighbors", {})
        rows = _records_from_preview_block(block, top_n=top_n)
        return {
            "ok": True,
            "mode": "preview_unknown_item_fallback",
            "data": rows,
            "message": "Đang dùng preview payload cho unknown product fallback.",
        }

    if not product_id:
        return {"ok": False, "message": "Vui lòng nhập product_id."}

    if model is None:
        preview_known_id = payload.get("recommendation_known_product_neighbors", {}).get("query_product_id")
        if product_id == str(preview_known_id):
            return _preview_known_product()
        return _preview_unknown_product()

    try:
        inner_iid = model.trainset.to_inner_iid(product_id)
        neighbor_ids = model.get_neighbors(inner_iid, k=top_n)

        rows = []
        for rank, ni in enumerate(neighbor_ids, start=1):
            raw_iid = model.trainset.to_raw_iid(ni)
            rows.append(
                {
                    "product_id": str(raw_iid),
                    "neighbor_rank": rank,
                    "reason": "item_knn_neighbors",
                }
            )

        df = pd.DataFrame(rows)
        df = _merge_product_metadata(df)

        return {
            "ok": True,
            "mode": "neighbors",
            "data": df.to_dict(orient="records"),
        }
    except Exception:
        if fallback is not None:
            work = fallback.copy()
            if "query_product_id" in work.columns:
                work["query_product_id"] = work["query_product_id"].astype(str)
                demo = work[work["query_product_id"] == product_id].copy()
                if demo.empty:
                    demo = work.head(top_n).copy()
            else:
                demo = work.head(top_n).copy()

            demo = _merge_product_metadata(demo)
            return {
                "ok": True,
                "mode": "fallback_neighbors_preview",
                "data": demo.head(top_n).to_dict(orient="records"),
            }

        return _preview_unknown_product()


# =========================================================
# FP-Growth helpers
# =========================================================
def get_association_rules(
    min_support: float = 0.0,
    min_confidence: float = 0.0,
    min_lift: float = 1.0,
    hide_unknown: bool = True,
    top_n: int = 50,
) -> dict[str, Any]:
    rules_df = load_metric_csv("association_rules.csv")
    if rules_df is None or rules_df.empty:
        preview = load_prediction_csv("top_association_rules_preview.csv")
        if preview is not None and not preview.empty:
            return {"ok": True, "mode": "preview", "data": preview.head(top_n)}
        return {"ok": False, "message": "Thiếu association_rules.csv."}

    try:
        work = rules_df.copy()

        for col in ["support", "confidence", "lift", "support_count"]:
            if col in work.columns:
                work[col] = pd.to_numeric(work[col], errors="coerce")

        if "support" in work.columns:
            work = work[work["support"] >= float(min_support)]
        if "confidence" in work.columns:
            work = work[work["confidence"] >= float(min_confidence)]
        if "lift" in work.columns:
            work = work[work["lift"] >= float(min_lift)]

        if hide_unknown:
            text_cols = [col for col in ["antecedents_str", "consequents_str", "rule_str"] if col in work.columns]
            if text_cols:
                mask = pd.Series(False, index=work.index)
                for col in text_cols:
                    mask = mask | work[col].astype(str).str.contains(r"\bunknown\b", case=False, na=False)
                work = work[~mask]

        sort_cols = [col for col in ["lift", "confidence", "support"] if col in work.columns]
        if sort_cols:
            work = work.sort_values(sort_cols, ascending=[False] * len(sort_cols))

        return {"ok": True, "mode": "model", "data": work.head(top_n)}
    except Exception as exc:
        return {"ok": False, "message": f"Lỗi lọc association rules: {exc}"}
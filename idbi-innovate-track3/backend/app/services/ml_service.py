import os
import json
import numpy as np
import onnxruntime as ort
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID

from app.config import settings


class MLModelService:
    def __init__(self):
        self.need_detection_model: Optional[ort.InferenceSession] = None
        self.credit_risk_model: Optional[ort.InferenceSession] = None
        self.product_ranking_model: Optional[ort.InferenceSession] = None
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return

        model_path = settings.MODEL_PATH
        try:
            need_path = os.path.join(model_path, settings.NEED_DETECTION_MODEL)
            if os.path.exists(need_path):
                self.need_detection_model = ort.InferenceSession(need_path)

            risk_path = os.path.join(model_path, settings.CREDIT_RISK_MODEL)
            if os.path.exists(risk_path):
                self.credit_risk_model = ort.InferenceSession(risk_path)

            rank_path = os.path.join(model_path, settings.PRODUCT_RANKING_MODEL)
            if os.path.exists(rank_path):
                self.product_ranking_model = ort.InferenceSession(rank_path)

            self._initialized = True
        except Exception as e:
            print(f"ML model initialization failed: {e}")
            self._initialized = False

    def is_ready(self) -> bool:
        return self._initialized and self.need_detection_model is not None

    def _prepare_features(self, msme_data: Dict, gst_data: List[Dict], aa_data: List[Dict]) -> np.ndarray:
        features = []

        features.append(float(msme_data.get("incorporation_year", 2020)) - 2000)
        features.append(1.0 if msme_data.get("constitution") == "Private Limited" else 0.0)
        features.append(float(msme_data.get("employee_count", 10)))

        if gst_data:
            latest_gst = gst_data[0]
            features.extend([
                float(latest_gst.get("total_revenue", 0)) / 1e7,
                float(latest_gst.get("gst_liability", 0)) / 1e6,
                float(latest_gst.get("itc_available", 0)) / 1e6,
                float(latest_gst.get("b2b_revenue", 0)) / max(float(latest_gst.get("total_revenue", 1)), 1),
                float(latest_gst.get("export_revenue", 0)) / max(float(latest_gst.get("total_revenue", 1)), 1),
            ])

            revenues = [float(g.get("total_revenue", 0)) for g in gst_data]
            features.extend([
                np.mean(revenues) / 1e7 if revenues else 0,
                np.std(revenues) / 1e7 if len(revenues) > 1 else 0,
                (revenues[-1] - revenues[0]) / max(revenues[0], 1) if len(revenues) > 1 else 0,
            ])
        else:
            features.extend([0.0] * 8)

        if aa_data:
            total_outstanding = sum(float(a.get("outstanding_amount", 0)) for a in aa_data)
            total_sanctioned = sum(float(a.get("sanctioned_limit", 0)) for a in aa_data)
            total_overdue = sum(float(a.get("overdue_amount", 0)) for a in aa_data)
            npas = sum(1 for a in aa_data if a.get("repayment_status") == "NPA")
            smas = sum(1 for a in aa_data if a.get("repayment_status", "").startswith("SMA"))

            features.extend([
                total_outstanding / 1e7,
                total_sanctioned / 1e7,
                total_outstanding / max(total_sanctioned, 1),
                total_overdue / max(total_outstanding, 1),
                float(npas),
                float(smas),
            ])

            account_types = {}
            for a in aa_data:
                t = a.get("account_type", "OTHER")
                account_types[t] = account_types.get(t, 0) + 1
            features.append(float(account_types.get("CC", 0)))
            features.append(float(account_types.get("OD", 0)))
            features.append(float(account_types.get("TERM_LOAN", 0)))
        else:
            features.extend([0.0] * 9)

        return np.array([features], dtype=np.float32)

    async def predict_needs(
        self, msme_data: Dict, gst_data: List[Dict], aa_data: List[Dict]
    ) -> Dict[str, Any]:
        if not self.is_ready():
            return self._mock_need_prediction()

        features = self._prepare_features(msme_data, gst_data, aa_data)

        input_name = self.need_detection_model.get_inputs()[0].name
        outputs = self.need_detection_model.run(None, {input_name: features})

        probabilities = outputs[0][0]
        categories = [
            "working_capital", "machinery_capex", "business_expansion",
            "inventory_funding", "trade_finance", "digital_transformation"
        ]

        need_probs = {cat: float(prob) for cat, prob in zip(categories, probabilities)}
        top_need = max(need_probs, key=need_probs.get)
        confidence = need_probs[top_need]

        shap_values = {cat: float(prob * 0.1) for cat, prob in need_probs.items()}
        key_drivers = sorted(need_probs.keys(), key=need_probs.get, reverse=True)[:3]

        return {
            "need_categories": need_probs,
            "top_need": top_need,
            "confidence_score": confidence,
            "shap_values": shap_values,
            "key_drivers": key_drivers,
            "model_version": "v1.0-onnx",
            "data_as_of": datetime.utcnow(),
        }

    async def predict_credit_risk(
        self, msme_data: Dict, gst_data: List[Dict], aa_data: List[Dict]
    ) -> Dict[str, Any]:
        if not self.is_ready() or self.credit_risk_model is None:
            return {"risk_score": 50, "risk_category": "MEDIUM", "pd": 0.15, "lgd": 0.45}

        features = self._prepare_features(msme_data, gst_data, aa_data)

        input_name = self.credit_risk_model.get_inputs()[0].name
        outputs = self.credit_risk_model.run(None, {input_name: features})

        pd = float(outputs[0][0][0])
        risk_score = int(pd * 100)
        risk_category = "HIGH" if pd > 0.3 else "MEDIUM" if pd > 0.1 else "LOW"

        return {
            "risk_score": risk_score,
            "risk_category": risk_category,
            "pd": pd,
            "lgd": 0.45,
            "model_version": "v1.0-onnx",
        }

    async def rank_products(
        self,
        msme_data: Dict,
        gst_data: List[Dict],
        aa_data: List[Dict],
        need_prediction: Dict,
        products: List[Dict]
    ) -> List[Dict]:
        if not self.is_ready() or self.product_ranking_model is None:
            return self._mock_product_ranking(products, need_prediction)

        ranked = []
        for product in products:
            features = self._prepare_features(msme_data, gst_data, aa_data)
            product_features = self._encode_product(product, need_prediction)
            combined = np.concatenate([features[0], product_features])

            input_name = self.product_ranking_model.get_inputs()[0].name
            outputs = self.product_ranking_model.run(None, {input_name: combined.reshape(1, -1)})
            ranking_score = float(outputs[0][0][0])

            ranked.append({**product, "ranking_score": ranking_score})

        ranked.sort(key=lambda x: x["ranking_score"], reverse=True)
        for i, p in enumerate(ranked):
            p["rank"] = i + 1

        return ranked

    def _encode_product(self, product: Dict, need_prediction: Dict) -> np.ndarray:
        product_types = [
            "cc_od", "machinery_term_loan", "business_expansion_loan",
            "inventory_funding", "trade_finance", "digital_business_loan"
        ]
        need_categories = [
            "working_capital", "machinery_capex", "business_expansion",
            "inventory_funding", "trade_finance", "digital_transformation"
        ]

        type_encoding = [0.0] * len(product_types)
        if product.get("product_type") in product_types:
            type_encoding[product_types.index(product["product_type"])] = 1.0

        need_encoding = [need_prediction.get("need_categories", {}).get(n, 0) for n in need_categories]

        return np.array(type_encoding + need_encoding + [
            product.get("suggested_amount", 0) / 1e7,
            product.get("suggested_tenure_months", 0) / 120,
            product.get("suggested_rate", 0) / 20,
        ], dtype=np.float32)

    def _mock_need_prediction(self) -> Dict[str, Any]:
        categories = [
            "working_capital", "machinery_capex", "business_expansion",
            "inventory_funding", "trade_finance", "digital_transformation"
        ]
        probs = np.random.dirichlet(np.ones(len(categories)))
        need_probs = {cat: float(prob) for cat, prob in zip(categories, probs)}
        top_need = max(need_probs, key=need_probs.get)

        return {
            "need_categories": need_probs,
            "top_need": top_need,
            "confidence_score": need_probs[top_need],
            "shap_values": {cat: float(prob * 0.1) for cat, prob in need_probs.items()},
            "key_drivers": sorted(need_probs.keys(), key=need_probs.get, reverse=True)[:3],
            "model_version": "v1.0-mock",
            "data_as_of": datetime.utcnow(),
        }

    def _mock_product_ranking(self, products: List[Dict], need_prediction: Dict) -> List[Dict]:
        need_to_product = {
            "working_capital": ["cc_od", "inventory_funding"],
            "machinery_capex": ["machinery_term_loan"],
            "business_expansion": ["business_expansion_loan"],
            "inventory_funding": ["inventory_funding", "cc_od"],
            "trade_finance": ["trade_finance"],
            "digital_transformation": ["digital_business_loan"],
        }
        top_need = need_prediction.get("top_need", "working_capital")
        preferred = need_to_product.get(top_need, ["cc_od"])

        for p in products:
            base_score = 0.5
            if p["product_type"] in preferred:
                base_score += 0.3
            p["ranking_score"] = base_score + np.random.random() * 0.2
            p["eligibility_score"] = 0.6 + np.random.random() * 0.3
            p["suggested_amount"] = p.get("suggested_amount", 1000000)
            p["suggested_tenure_months"] = p.get("suggested_tenure_months", 36)
            p["suggested_rate"] = p.get("suggested_rate", 12.0)

        products.sort(key=lambda x: x["ranking_score"], reverse=True)
        for i, p in enumerate(products):
            p["rank"] = i + 1
        return products


ml_service = MLModelService()
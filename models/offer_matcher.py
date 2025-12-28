from typing import List, Dict
from pathlib import Path
import json
from datetime import date
from utils.auxiliar import normalize

from schemas.cv import ExtractedCVData

# =====================
# CARGA DE OFERTAS
# =====================
OFFERS_PATH = Path("data/ofertas_activas.json")

with open(OFFERS_PATH, "r", encoding="utf-8") as f:
    ALL_OFFERS = json.load(f)

ACTIVE_OFFERS = [
    o for o in ALL_OFFERS
    if o.get("activo") is True
]

# =====================
# HELPERS
# =====================

def text_contains_any(text: str, keywords: List[str]) -> bool:
    text_norm = normalize(text)
    return any(kw in text_norm for kw in keywords)

# =====================
# MATCHER PRINCIPAL
# =====================

async def match_offers(
    candidate_data: ExtractedCVData,
    recommended_positions: List[str]
) -> List[Dict]:

    results = []

    exp_titles = [normalize(exp.title) for exp in candidate_data.experience]
    skills = [normalize(s) for s in candidate_data.skills]

    exp_text = " ".join(exp_titles)
    skills_text = " ".join(skills)

    for offer in ACTIVE_OFFERS:
        score = 0
        reasons = []

        # 1️⃣ Puesto recomendado
        if offer["puesto"] in recommended_positions:
            score += 40
            reasons.append("Puesto recomendado para el candidato")

        # 2️⃣ Experiencia relacionada
        if text_contains_any(exp_text, normalize(offer["puesto"]).split()):
            score += 30
            reasons.append("Experiencia previa relacionada")

        # 3️⃣ Skills
        if offer.get("descripcion") and text_contains_any(
            offer["descripcion"], skills_text
        ):
            score += 20
            reasons.append("Habilidades coincidentes")

        # 4️⃣ Categoría
        if normalize(offer["categoria"]) in exp_text:
            score += 10
            reasons.append("Categoría compatible")

        if score > 0:
            results.append({
                "offer_id": offer["id"],
                "puesto": offer["puesto"],
                "empresa": offer["empresa"],
                "score": min(score, 100),
                "reasons": reasons
            })

    return sorted(results, key=lambda x: x["score"], reverse=True)

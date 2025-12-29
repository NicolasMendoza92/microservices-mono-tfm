from typing import List, Dict
from utils.auxiliar import normalize
from schemas.cv import ExtractedCVData
# from models.offers.repository import get_active_offers
from sqlalchemy.ext.asyncio import AsyncSession
from models.offers.loader import load_offers

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
    recommended_positions: List[str],
    db: AsyncSession | None = None
) -> List[Dict]:

    offers = await load_offers(db)
    results = []

    exp_titles = [normalize(exp.title) for exp in candidate_data.experience]
    skills = [normalize(skill) for skill in candidate_data.skills]

    exp_text = " ".join(exp_titles)
    skills_text = " ".join(skills)

    for offer in offers:
        # Unificar acceso
        is_dict = isinstance(offer, dict)

        puesto = offer["puesto"] if is_dict else offer.puesto
        categoria = offer["categoria"] if is_dict else offer.categoria
        empresa = offer["empresa"] if is_dict else offer.empresa
        descripcion = offer.get("descripcion") if is_dict else offer.descripcion
        offer_id = offer["id"] if is_dict else offer.id

        score = 0
        reasons = []

        if puesto in recommended_positions:
            score += 40
            reasons.append("Puesto recomendado para el candidato")

        if text_contains_any(exp_text, normalize(puesto).split()):
            score += 30
            reasons.append("Experiencia previa relacionada")

        if descripcion and text_contains_any(
            normalize(descripcion),
            skills_text
        ):
            score += 20
            reasons.append("Habilidades coincidentes")

        if categoria and normalize(categoria) in exp_text:
            score += 10
            reasons.append("Categoría compatible")

        if score > 0:
            results.append({
                "offer_id": offer_id,
                "puesto": puesto,
                "empresa": empresa,
                "score": min(score, 100),
                "reasons": reasons
            })

    return sorted(results, key=lambda x: x["score"], reverse=True)

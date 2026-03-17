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

    # Normalizar recomendaciones UNA sola vez
    recommended_norm = [normalize(p) for p in recommended_positions]

    exp_titles = [normalize(exp.title) for exp in candidate_data.experience if exp.title]
    skills = [normalize(skill) for skill in candidate_data.skills if skill]
    exp_text = " ".join(exp_titles)
    print("OFFERSSSSSSSSSSS", offers)

    for offer in offers:
        is_dict = isinstance(offer, dict)

        puesto      = offer["puesto"]      if is_dict else offer.puesto
        categoria   = offer["categoria"]   if is_dict else offer.categoria
        empresa     = offer["empresa"]     if is_dict else offer.empresa
        descripcion = offer.get("descripcion") if is_dict else offer.descripcion
        offer_id    = offer["id"]          if is_dict else offer.id

        puesto_norm = normalize(puesto)  # 👈 normalizar el puesto de la BD

        score = 0
        reasons = []

        # 1. Puesto recomendado ✅ comparación normalizada
        if puesto_norm in recommended_norm:
            score += 40
            reasons.append("Puesto recomendado para el candidato")

        # 2. Experiencia relacionada
        if text_contains_any(exp_text, puesto_norm.split()):
            score += 30
            reasons.append("Experiencia previa relacionada")

        # 3. Skills en descripción
        if descripcion and skills:
            if text_contains_any(normalize(descripcion), skills):
                score += 20
                reasons.append("Habilidades coincidentes")

        # 4. Categoría compatible
        if categoria and text_contains_any(exp_text, normalize(categoria).split()):
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
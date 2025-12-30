from typing import List, Dict
from utils.auxiliar import normalize

def match_candidates_from_offer(
    offer: Dict,
    candidates: List[Dict],
    limit: int = 10
) -> List[Dict]:

    results = []

    offer_puesto = normalize(offer["puesto"])
    offer_desc = normalize(offer.get("descripcion", ""))
    offer_cat = normalize(offer.get("categoria", ""))

    for c in candidates:
        score = 0
        reasons = []

        exp_titles = " ".join(
            normalize(exp.get("title", ""))
            for exp in c["experience"]
        )

        skills_text = " ".join(
            normalize(s) for s in c["skills"]
        )

        # 1 Puesto
        if offer_puesto in exp_titles:
            score += 40
            reasons.append("Experiencia directa en el puesto")

        # 2 Experiencia relacionada
        if offer_desc and any(w in exp_titles for w in offer_desc.split()):
            score += 25
            reasons.append("Experiencia relacionada")

        # 3 Skills
        if offer_desc and any(s in offer_desc for s in skills_text.split()):
            score += 25
            reasons.append("Habilidades relevantes")

        # 4 Categoría
        if offer_cat and offer_cat in exp_titles:
            score += 10
            reasons.append("Categoría compatible")

        if score > 0:
            results.append({
                "id": c["id"],
                "name": c["name"],
                "email": c["email"],
                "phone": c["phone"],
                "current_position": (
                    c["experience"][0]["title"]
                    if c["experience"] else None
                ),
                "match_percentage": min(score, 100),
                "reasons": reasons
            })

    results.sort(key=lambda x: x["match_percentage"], reverse=True)
    return results[:limit]

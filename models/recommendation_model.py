
from typing import List
from schemas.cv import ExtractedCVData
import json
from pathlib import Path
import unicodedata
import re
from utils.auxiliar import normalize

CATALOG_PATH = Path("data/puestos_keywords.json")

with open(CATALOG_PATH, "r", encoding="utf-8") as f:
    PUESTOS_CATALOG = json.load(f)


def experience_matches_puesto(
    exp_title: str,
    puesto_keywords: List[str],
    min_matches: int = 1
) -> bool:
    title_norm = normalize(exp_title)
    matches = sum(1 for kw in puesto_keywords if kw in title_norm)
    return matches >= min_matches

async def recommend_jobs(processed_cv_data: ExtractedCVData) -> list[str]:
    experience_items = processed_cv_data.experience or []
    recommendations = set()

    for exp in experience_items:
        if not exp.title or exp.years <= 0:
            continue
        
        title_word_count = len(normalize(exp.title).split())

        for puesto in PUESTOS_CATALOG:
            min_matches = 1 if title_word_count <= 2 else 2

            if experience_matches_puesto(
                exp.title,
                puesto["keywords"],
                min_matches=min_matches
            ):
                recommendations.add(puesto["puesto"])
                
    if not recommendations:
        recommendations.add("Puestos operativos generales")

    return list(recommendations)

import json
from pathlib import Path
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from models.candidate.repository import get_candidates_for_matching

# ==================================
# CONFIG
# ==================================
CANDIDATES_SOURCE = "db"  # 👈 "json" | "db"
CANDIDATES_PATH = Path("data/candidates_mock.json")

print(f"[Candidates loader] Fuente seleccionada: {CANDIDATES_SOURCE}")

# ==================================
# LOADER
# ==================================
async def load_candidates(
    db: AsyncSession | None = None
) -> List[Dict]:

    # -------- JSON LOCAL --------
    if CANDIDATES_SOURCE == "json":
        with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    # -------- DATABASE --------
    if CANDIDATES_SOURCE == "db":
        if db is None:
            raise ValueError(
                "DB session requerida cuando CANDIDATES_SOURCE='db'"
            )
        return await get_candidates_for_matching(db)

    raise ValueError(f"CANDIDATES_SOURCE inválido: {CANDIDATES_SOURCE}")

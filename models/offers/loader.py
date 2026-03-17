import json
from pathlib import Path
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from models.offers.repository import get_active_offers

OFFERS_SOURCE = "db"  # 👈 cambiar aqui si queremos usar la "db" o queremos usar el "json" que esta en el reposotirio /data/ofertas_activas.json
OFFERS_PATH = Path("data/ofertas_activas.json")

print(f'seleccionada {OFFERS_SOURCE}')

async def load_offers(db: AsyncSession | None = None) -> List:
    if OFFERS_SOURCE == "db":
        if db is None:
            raise ValueError("DB session requerida cuando OFFERS_SOURCE='db'")
        
        offers = await get_active_offers(db)
        print(f"[load_offers] Ofertas traídas de DB: {len(offers)}")
        print(f"[load_offers] Primera oferta: {offers[0] if offers else 'NINGUNA'}")
        return offers

from sqlalchemy import select
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from models.offers.model import Offer

async def get_active_offers(db: AsyncSession):
    today = date.today()
    print(f"[get_active_offers] Buscando ofertas activas para fecha: {today}")

    result = await db.execute(
        select(Offer).where(
            Offer.activo.is_(True),
            Offer.fechaInicio <= today,
            Offer.fechaFin >= today
        )
    )

    offers = result.scalars().all()
    print(f"[get_active_offers] Total encontradas: {len(offers)}")
    return offers
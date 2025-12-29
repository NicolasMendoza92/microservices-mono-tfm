from sqlalchemy import select
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from models.offers.model import Offer

async def get_active_offers(db: AsyncSession):
    today = date.today()

    result = await db.execute(
        select(Offer).where(
            Offer.activo.is_(True),
            Offer.fechaInicio <= today,
            Offer.fechaFin >= today
        )
    )

    return result.scalars().all()

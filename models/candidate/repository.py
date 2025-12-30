from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.candidate.model import Candidate

async def get_candidates_for_matching(
    db: AsyncSession
):
    stmt = select(
        Candidate.id,
        Candidate.name,
        Candidate.email,
        Candidate.phone,
        Candidate.experience,
        Candidate.skills
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Convertimos a dicts simples
    return [
        {
            "id": r.id,
            "name": r.name,
            "email": r.email,
            "phone": r.phone,
            "experience": r.experience or [],
            "skills": r.skills or []
        }
        for r in rows
    ]

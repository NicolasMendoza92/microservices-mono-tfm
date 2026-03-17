from sqlalchemy import Column, Integer, String, Boolean, Date
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel
from typing import List

Base = declarative_base()

class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True)
    puesto = Column(String)
    categoria = Column(String)
    empresa = Column(String)
    descripcion = Column(String)
    activo = Column(Boolean)
    fechaInicio = Column(Date)
    fechaFin = Column(Date)
    createdAt=Column(Date)
    
class OfferMatch(BaseModel):
    id: int
    puesto: str
    empresa: str
    match_percentage: int
    reasons: List[str]

class OfferMatcherSummary(BaseModel):
    total_offers: int
    matched_offers: int
    best_match_score: int

class OfferMatcherResponse(BaseModel):
    summary: OfferMatcherSummary
    offers: List[OfferMatch]
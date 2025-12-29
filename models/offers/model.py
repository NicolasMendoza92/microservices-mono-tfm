from sqlalchemy import Column, Integer, String, Boolean, Date
from sqlalchemy.orm import declarative_base

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
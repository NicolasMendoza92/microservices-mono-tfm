# schemas/cv.py

from pydantic import BaseModel
from typing import List, Optional

class ExperienceItem(BaseModel):
    title: str
    company: str
    years: int
    # Puedes añadir start_date: Optional[str], end_date: Optional[str], description: Optional[str] etc.

class EducationItem(BaseModel):
    degree: str
    institution: str
    year: Optional[int]
    # Puedes añadir start_date: Optional[str], end_date: Optional[str] etc.

class LanguageItem(BaseModel):
    name: str
    level: str

class ExtractedCVData(BaseModel):
    """
    Representa la información extraída de un CV por el microservicio PLN.
    """
    id: str # Debería ser el ID del archivo o del candidato
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    experience: List[ExperienceItem] = []
    education: List[EducationItem] = []
    skills: List[str] = []
    languages: List[LanguageItem] = []
    summary: Optional[str] = None # Resumen profesional o descripción breve
    raw_text: Optional[str] = None # Texto completo extraído (útil para debug o otros modelos)
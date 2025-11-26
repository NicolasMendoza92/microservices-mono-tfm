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
    id: str 
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    experience: List[ExperienceItem] = []
    education: List[EducationItem] = []
    skills: List[str] = []
    languages: List[LanguageItem] = []
    summary: Optional[str] = None
    raw_text: Optional[str] = None 
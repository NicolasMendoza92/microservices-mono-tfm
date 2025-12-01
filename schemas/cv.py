from pydantic import BaseModel
from typing import List, Optional

class ExperienceItem(BaseModel):
    title: str
    years: int

class EducationItem(BaseModel):
    degree: str
    year: Optional[int]

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
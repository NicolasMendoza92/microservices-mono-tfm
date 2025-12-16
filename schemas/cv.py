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

class CandidateData(BaseModel):
    id: str
    name: str
    summary: Optional[str] = None
    experience: List[ExperienceItem] = []
    education: List[EducationItem] = []
    skills: List[str] = []
    languages: List[LanguageItem] = []
    gender: Optional[str] = None     
    age: Optional[int] = None
    maritalStatus: Optional[str] = None
    birthCountry: Optional[str] = None
    numLanguages: Optional[int] = None
    hasCar: Optional[bool] = None
    criminalRecord: Optional[bool] = None
    restrainingOrder: Optional[bool] = None
    numChildren: Optional[int] = None
    workDisability: Optional[bool] = None
    disabilityFlag: Optional[bool] = None
    jobSeeker: Optional[bool] = None
    weaknesses: Optional[str] = None
    trainingProfile: Optional[str] = None
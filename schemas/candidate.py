from pydantic import BaseModel
from typing import List, Optional

# Esquema para la información extraída del CV (input para los modelos)
class CVProcessedData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = []
    experience: List[dict] = []  
    education: List[dict] = []   
    raw_text: str 


# Esquema de salida para el resumen del candidato
class CandidateSummary(BaseModel):
    id: str
    name: str
    employability_score: float
    top_recommendations: List[str]
    last_processed: str
    areas_for_development: List[str] = [] 
    interview_questions: Optional[List[str]] = None 

# Esquema para la respuesta de error
class ErrorResponse(BaseModel):
    detail: str
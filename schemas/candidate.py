from pydantic import BaseModel
from typing import List, Optional

# Esquema para la información extraída del CV (input para los modelos)
class CVProcessedData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = []
    experience: List[dict] = []  # Ejemplo: [{"title": "Dev", "company": "X", "years": 2}]
    education: List[dict] = []   # Ejemplo: [{"degree": "Ing.", "institution": "U", "year": 2020}]
    raw_text: str # Todo el texto extraído del CV
    # ... y cualquier otra data relevante que extraigas

# Esquema de salida para el resumen del candidato
class CandidateSummary(BaseModel):
    id: str
    name: str
    employability_score: float
    top_recommendations: List[str]
    last_processed: str
    areas_for_development: List[str] = [] # Del modelo de empleabilidad
    interview_questions: Optional[List[str]] = None # Opcional, si implementas el microservicio

# Esquema para la respuesta de error
class ErrorResponse(BaseModel):
    detail: str
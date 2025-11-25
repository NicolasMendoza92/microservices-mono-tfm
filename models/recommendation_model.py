# models/recommendation_model.py

from typing import List, Dict, Any
from schemas.cv import ExtractedCVData

# Simula la carga de tu modelo de clustering (K-Means, DBSCAN)
# y la lista de posibles puestos
# job_clusters = joblib.load("path/to/your/job_clusters.pkl")
# job_titles_mapping = ...

async def recommend_jobs(processed_cv_data: Dict[str, Any]) -> List[str]:
    """
    Recomienda puestos de trabajo basados en los datos extraídos del CV.
    """
    skills = processed_cv_data.get("skills", [])
    experience = processed_cv_data.get("experience", [])
    summary = processed_cv_data.get("summary", "").lower()
    
    recommendations = []

    # Lógica basada en habilidades
    if any(s.lower() in ["python", "javascript", "sql", "machine learning"] for s in skills):
        recommendations.append("Desarrollador de Software")
        recommendations.append("Analista de Datos")
    if any(s.lower() in ["supervisión de equipos", "control de calidad", "producción"] for s in skills):
        recommendations.append("Supervisor de Producción")
        recommendations.append("Encargado de Operaciones")
    if any(s.lower() in ["atención al cliente", "ventas", "comunicación"] for s in skills):
        recommendations.append("Asesor Comercial")
        recommendations.append("Ejecutivo de Atención al Cliente")
    if any(s.lower() in ["contabilidad", "finanzas", "excel"] for s in skills):
        recommendations.append("Auxiliar Contable")
        recommendations.append("Asistente Administrativo")

    # Lógica basada en experiencia
    if any(exp["title"].lower() == "operario de línea" for exp in experience):
        recommendations.append("Operario de Fábrica")
    if any(exp["title"].lower() == "mozo de almacén" for exp in experience):
        recommendations.append("Operador de Bodega")

    # Lógica basada en el resumen (palabras clave)
    if "logística" in summary or "inventario" in summary:
        recommendations.append("Asistente de Logística")
    if "gestión de proyectos" in summary:
        recommendations.append("Coordinador de Proyectos")

    # Si no hay recomendaciones específicas, añadir generales
    if not recommendations:
        recommendations.append("Roles de entrada sin experiencia específica")
        recommendations.append("Aprendiz en diferentes áreas")
        
    return list(set(recommendations)) # Eliminar duplicados
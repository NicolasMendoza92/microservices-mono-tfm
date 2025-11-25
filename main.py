# main.py

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from typing import Dict, Any, List
from uuid import uuid4
import os
import datetime

from config import add_cors_middleware
from schemas.cv import ExtractedCVData
from schemas.candidate import CandidateSummary, CVProcessedData, ErrorResponse
from utils.file_handler import save_upload_file, UPLOAD_DIR
# from models.cv_processing import process_cv_with_huggingface_ner as process_cv_with_pln # Renombrar para no cambiar las llamadas
from models.cv_processing import extract_text_from_file, extract_cv_data_from_text # Nuevas funciones del PLN
from models.employability_model import predict_employability
from models.recommendation_model import recommend_jobs
from models.interview_prep import generate_interview_questions # Opcional

app = FastAPI(
    title="T3 Chat - API de Inclusión Laboral",
    description="API para procesar CVs, evaluar empleabilidad, recomendar puestos y generar preguntas de entrevista para personas en reclusión.",
    version="1.0.0",
)

# Añadir el middleware CORS
add_cors_middleware(app)

# Variable para almacenar los datos procesados de los candidatos (para este ejemplo simple)
# En un entorno real, esto iría a una base de datos.
processed_candidates_db: Dict[str, CVProcessedData] = {}
extracted_data_db: Dict[str, ExtractedCVData] = {}
candidate_summaries_db: Dict[str, CandidateSummary] = {}


@app.get("/", summary="Endpoint de prueba")
async def read_root():
    return {"message": "Bienvenido a la API de Inclusión Laboral"}

@app.post(
    "/extract-cv-data",
    response_model=ExtractedCVData,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Extrae información de un CV con PLN para revisión",
    responses={
        202: {"description": "CV recibido y extracción de datos iniciada"},
        400: {"model": dict, "description": "Formato de archivo no soportado o error al procesar CV"}, # dict para error
        500: {"model": dict, "description": "Error interno del servidor"}
    }
)

@app.post(
    "/process-cv",
    response_model=CandidateSummary,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Procesar CV y obtener resumen del candidato",
    responses={
        202: {"description": "CV recibido y procesamiento iniciado"},
        400: {"model": ErrorResponse, "description": "Formato de archivo no soportado o error al procesar CV"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def extract_cv_data_endpoint(file: UploadFile = File(...)):
    """
    Recibe un archivo CV (PDF, DOCX, TXT), extrae su texto
    y luego utiliza un modelo PLN (Hugging Face) para estructurar
    la información clave. Estos datos son para revisión del usuario.
    """
    candidate_id = str(uuid4()) # Usamos este ID para el seguimiento

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se ha proporcionado un nombre de archivo."
        )

    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in [".pdf", ".docx", ".txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de archivo no soportado: {file_extension}. "
                   "Solo se aceptan PDF, DOCX y TXT."
        )

    file_location = ""
    try:
        file_location = await save_upload_file(file)
        raw_text = await extract_text_from_file(file_location)
        
        # Llama a la nueva función de extracción y estructuración
        extracted_data = await extract_cv_data_from_text(raw_text, candidate_id)
        
        # Guarda los datos extraídos para posible recuperación o para el siguiente paso
        extracted_data_db[candidate_id] = extracted_data
        
        return extracted_data

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Error inesperado al extraer datos del CV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor al procesar el CV: {e}"
        )
    finally:
        if os.path.exists(file_location):
            os.remove(file_location)


# Segundo endpoint: Recibe los datos ya extraídos (y posiblemente modificados) y ejecuta los modelos de ML
@app.post(
    "/process-candidate-data",
    response_model=CandidateSummary,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Procesa los datos de un candidato para generar un resumen de empleabilidad",
    responses={
        202: {"description": "Datos del candidato recibidos y procesamiento iniciado"},
        400: {"model": dict, "description": "Datos de entrada inválidos"},
        500: {"model": dict, "description": "Error interno del servidor"}
    }
)
async def process_candidate_data_endpoint(candidate_data: ExtractedCVData):
    """
    Recibe la información estructurada de un CV (que ha sido revisada/aprobada
    por el usuario), la utiliza para predecir la empleabilidad,
    recomendar puestos y generar preguntas de entrevista.
    """
    # Usamos el ID de los datos extraídos como ID del candidato para el summary
    candidate_id = candidate_data.id

    try:
        # Asegúrate de que los datos extraídos estén en un formato que tus modelos esperan.
        # Puede que necesites una función de mapeo/transformación aquí.
        
        # 1. Evaluación de empleabilidad (Microservicio 2)
        # El modelo de empleabilidad necesita los datos en un formato específico
        employability_results = await predict_employability(candidate_data.dict())

        # 2. Recomendación de puestos (Microservicio 3)
        job_recommendations = await recommend_jobs(candidate_data.dict())

        # 3. Microservicio opcional: Preparación de entrevista
        interview_questions = await generate_interview_questions(
            candidate_name=candidate_data.name if candidate_data.name else "Candidato",
            skills=candidate_data.skills,
            experience=candidate_data.experience,
            areas_for_development=employability_results.get("areas_for_development", []),
            job_recommendations=job_recommendations
        )

        # Construir el resumen final del candidato
        summary = CandidateSummary(
            id=candidate_id,
            name=candidate_data.name if candidate_data.name else "Candidato Desconocido",
            employability_score=employability_results["employability_score"],
            top_recommendations=job_recommendations,
            last_processed=datetime.datetime.now().isoformat(),
            areas_for_development=employability_results["areas_for_development"],
            interview_questions=interview_questions
        )
        candidate_summaries_db[candidate_id] = summary
        
        return summary

    except Exception as e:
        print(f"Error inesperado al procesar los datos del candidato: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor al procesar los datos: {e}"
        )

@app.get(
    "/candidate-summary/{candidate_id}",
    response_model=CandidateSummary,
    summary="Obtener el resumen de un candidato por ID",
    responses={
        200: {"description": "Resumen del candidato encontrado"},
        404: {"model": ErrorResponse, "description": "Candidato no encontrado"}
    }
)
async def get_candidate_summary(candidate_id: str):
    """
    Permite obtener el resumen de un candidato previamente procesado
    usando su ID único.
    """
    summary = candidate_summaries_db.get(candidate_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidato con ID '{candidate_id}' no encontrado."
        )
    return summary

# Para ejecutar: uvicorn main:app --reload
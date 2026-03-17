# main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from typing import Dict
from uuid import uuid4
import os
import datetime
from config import add_cors_middleware
from schemas.cv import ExtractedCVData, CandidateData
from schemas.candidate import CandidateSummary, CVProcessedData
from schemas.offer import OfferInput
from fastapi import Depends
from db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from utils.file_handler import save_upload_file
from models.cv_processing import extract_text_from_file, extract_cv_data_from_text
from models.employability_model import predict_employability
from models.recommendation_model import recommend_jobs
from models.interview_prep import generate_interview_questions 
from models.offers.matcher import match_offers
from models.candidate.matcher import match_candidates_from_offer
from models.candidate.loader import load_candidates
from models.offers.model import Offer, OfferMatcherResponse, OfferMatcherSummary, OfferMatch

app = FastAPI(
    title="T3 Chat - API de Inclusión Laboral",
    description="API para procesar CVs, evaluar empleabilidad, recomendar puestos y generar preguntas de entrevista para personas en reclusión.",
    version="1.0.0",
)

# Añadir el middleware CORS
add_cors_middleware(app)

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

async def extract_cv_data_endpoint(file: UploadFile = File(...)):
    candidate_id = str(uuid4()) 

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
        
        # Microservicio 1 - despues de que saca la info con hugging NER envio el texto plano a esta funcion
        extracted_data = await extract_cv_data_from_text(raw_text, candidate_id, file.filename)
        
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
async def process_candidate_data_endpoint(candidate_data: CandidateData):
    # Usamos el ID de los datos extraídos como ID del candidato para el summary
    candidate_id = candidate_data.id

    try:
        # 1. Evaluación de empleabilidad (Microservicio 2)
        employability_results = await predict_employability(candidate_data)

        # 2. Recomendación de puestos (Microservicio 3)
        job_recommendations = await recommend_jobs(candidate_data)

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


@app.post(
    "/offer-matcher",
    response_model=OfferMatcherResponse,
    status_code=status.HTTP_200_OK,
    summary="Busca ofertas compatibles con el perfil de un candidato",
    responses={
        400: {"description": "Datos del candidato insuficientes"},
        500: {"description": "Error interno al procesar el matching"},
    }
)
async def offer_matcher(
    candidate_data: ExtractedCVData,
    db: AsyncSession = Depends(get_db)
) -> OfferMatcherResponse:

    # Validación mínima: sin experiencia ni skills no hay matching útil
    if not candidate_data.experience and not candidate_data.skills:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El candidato debe tener al menos experiencia o habilidades para buscar ofertas."
        )
    print("SKILLS:", candidate_data.skills)
    print("EXPERIENCE:", candidate_data.experience)

    try:
        job_recommendations = await recommend_jobs(candidate_data)
        print("RECOMENDACIONES:", job_recommendations)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar recomendaciones de puestos: {e}"
        )

    try:
        matched_offers = await match_offers(
            candidate_data=candidate_data,
            recommended_positions=job_recommendations,
            db=db
        )
        print("MATCHES:", len(matched_offers))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al buscar ofertas compatibles: {e}"
        )

    best_score = matched_offers[0]["score"] if matched_offers else 0

    return OfferMatcherResponse(
        summary=OfferMatcherSummary(
            total_offers=len(matched_offers),
            matched_offers=len(matched_offers),
            best_match_score=best_score,
        ),
        offers=[
            OfferMatch(
                id=o["offer_id"],
                puesto=o["puesto"],
                empresa=o["empresa"],
                match_percentage=o["score"],
                reasons=o["reasons"],
            )
            for o in matched_offers
        ]
    )

@app.post("/candidate-matcher")
async def candidate_matcher(
    offer: OfferInput,
    db: AsyncSession = Depends(get_db)
):
    candidates = await load_candidates(db)

    matches = match_candidates_from_offer(
        offer=offer.model_dump(),
        candidates=candidates
    )

    return {
        "summary": {
            "total_candidates": len(candidates),
            "matched_candidates": len(matches),
            "best_match_score": matches[0]["match_percentage"] if matches else 0
        },
        "candidates": matches
    }

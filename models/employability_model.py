# models/employability_model.py
import joblib
from typing import List, Dict, Any
from schemas.cv import ExtractedCVData

# Simula la carga de un modelo. En un entorno real, cargarías un archivo .pkl o .h5
# model = joblib.load("path/to/your/employability_model.pkl") # Descomentar y usar tu modelo real
MODEL_LOADED = False # Solo para la simulación, en realidad sería el modelo cargado
if not MODEL_LOADED: # Simulate loading
    print("Cargando modelo de empleabilidad (simulado)...")
    # Aquí iría la carga real: model = joblib.load(...)
    MODEL_LOADED = True

def _transform_data_for_employability_model(processed_cv_data: ExtractedCVData) -> List[float]:

    skills = processed_cv_data.skills if processed_cv_data.skills is not None else []
    experience_items = processed_cv_data.experience if processed_cv_data.experience is not None else []
    education_items = processed_cv_data.education if processed_cv_data.education is not None else []
    
    num_skills = len(skills)
    # total_experience_years = sum(exp.get("years", 0) for exp in processed_cv_data.experience) # Anterior
    total_experience_years = sum(exp.years for exp in experience_items) # <-- CORREGIDO: accedes a exp.years
    num_education_items = len(education_items)
    
    # Simulación de otras características
    has_email = 1 if processed_cv_data.email else 0 # <-- CORREGIDO
    # Accede al summary con punto, y luego verifica su longitud
    has_summary = 1 if processed_cv_data.summary and len(processed_cv_data.summary) > 50 else 0 # <-- CORREGIDO

    # Este array debe coincidir con el número y orden de características del modelo entrenado.
    features = [
        float(num_skills),
        float(total_experience_years),
        float(num_education_items),
        float(has_email),
        float(has_summary),
        # ... añade más características derivadas de ExtractedCVData
    ]
    return features

async def predict_employability(processed_cv_data: ExtractedCVData) -> Dict[str, Any]:

    model_features = _transform_data_for_employability_model(processed_cv_data)

    # --- SIMULACIÓN DEL MODELO ---
    score = (model_features[0] * 0.05 + 
             model_features[1] * 0.1 + 
             model_features[2] * 0.02 + 
             model_features[3] * 0.01 + 
             model_features[4] * 0.03 
             )
    score = min(1.0, max(0.1, score)) # Asegura que esté entre 0.1 y 1.0

    areas_for_development = []
    if score < 0.5:
        areas_for_development.append("Necesita desarrollar más habilidades específicas.")
    if model_features[1] < 2: 
        areas_for_development.append("Ganar más experiencia práctica en el sector.")
    if "Comunicación" not in (processed_cv_data.skills if processed_cv_data.skills else []):
        areas_for_development.append("Mejorar habilidades de comunicación y soft skills.")

    return {
        "employability_score": round(score, 2),
        "areas_for_development": areas_for_development
    }
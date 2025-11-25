# models/employability_model.py
import joblib
from typing import List, Dict, Any
from schemas.cv import ExtractedCVData

# Simula la carga de un modelo. En un entorno real, cargarías un archivo .pkl o .h5
# model = joblib.load("path/to/your/employability_model.pkl") # Descomentar y usar tu modelo real

def _transform_data_for_employability_model(processed_cv_data: Dict[str, Any]) -> List[float]:
    """
    Función helper para transformar los datos procesados del CV (ExtractedCVData en dict)
    en el formato numérico que espera tu modelo de empleabilidad.
    """
    # ¡IMPORTANTE! Asegúrate de que esta lógica coincida con tu Feature Engineering REAL
    # Aquí es donde mapeas ExtractedCVData a un vector de características numéricas.

    num_skills = len(processed_cv_data.get("skills", []))
    total_experience_years = sum(exp.get("years", 0) for exp in processed_cv_data.get("experience", []))
    num_education_items = len(processed_cv_data.get("education", []))
    
    # Simulación de otras características
    has_email = 1 if processed_cv_data.get("email") else 0
    has_summary = 1 if processed_cv_data.get("summary") and len(processed_cv_data["summary"]) > 50 else 0

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

async def predict_employability(processed_cv_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predice el score de empleabilidad y sugiere áreas de desarrollo.
    """
    model_features = _transform_data_for_employability_model(processed_cv_data)

    # --- SIMULACIÓN DEL MODELO ---
    score = (model_features[0] * 0.05 + # habilidades
             model_features[1] * 0.1 + # experiencia
             model_features[2] * 0.02 + # educación
             model_features[3] * 0.01 + # tiene email
             model_features[4] * 0.03 # tiene resumen
             )
    score = min(1.0, max(0.1, score)) # Asegura que esté entre 0.1 y 1.0

    areas_for_development = []
    if score < 0.5:
        areas_for_development.append("Necesita desarrollar más habilidades específicas.")
    if model_features[1] < 2: # Menos de 2 años de experiencia simulada
        areas_for_development.append("Ganar más experiencia práctica en el sector.")
    if "Comunicación" not in processed_cv_data.get("skills", []):
        areas_for_development.append("Mejorar habilidades de comunicación y soft skills.")

    return {
        "employability_score": round(score, 2),
        "areas_for_development": areas_for_development
    }
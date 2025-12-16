# models/employability_model.py

import os
import joblib
import pandas as pd  # Necesitamos pandas para el feature engineering
import unicodedata
from rapidfuzz import process
from sklearn.preprocessing import MultiLabelBinarizer
from typing import List, Dict, Any, Optional  # Optional para el modelo y features
from schemas.cv import CandidateData
from utils.tags import etiquetas

# --- Rutas para la carga del modelo y features ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
TRAINED_MODELS_DIR = os.path.join(PROJECT_ROOT, "trained_models")

EMPLOYABILITY_MODEL_PATH = os.path.join(
    TRAINED_MODELS_DIR, "empleabilidad_model.joblib"
)
FEATURE_COLUMNS_PATH = os.path.join(TRAINED_MODELS_DIR, "empleabilidad_features.joblib")

# --- Cargar el modelo real y las columnas de features ---
employability_model: Optional[Any] = None
expected_feature_columns: Optional[List[str]] = None

try:
    if os.path.exists(EMPLOYABILITY_MODEL_PATH):
        employability_model = joblib.load(EMPLOYABILITY_MODEL_PATH)
        print(
            f"Modelo de empleabilidad cargado exitosamente desde: {EMPLOYABILITY_MODEL_PATH}"
        )
    else:
        print(
            f"ADVERTENCIA: Archivo del modelo de empleabilidad no encontrado en: {EMPLOYABILITY_MODEL_PATH}. Se usará una simulación."
        )
except Exception as e:
    print(
        f"ERROR al cargar el modelo de empleabilidad desde {EMPLOYABILITY_MODEL_PATH}: {e}. Se usará una simulación."
    )
    employability_model = None

try:
    if os.path.exists(FEATURE_COLUMNS_PATH):
        expected_feature_columns = joblib.load(FEATURE_COLUMNS_PATH)
        print(
            f"Columnas de features cargadas exitosamente desde: {FEATURE_COLUMNS_PATH} ({len(expected_feature_columns)} features)"
        )
    else:
        print(
            f"ADVERTENCIA: Archivo de columnas de features no encontrado en: {FEATURE_COLUMNS_PATH}. La predicción podría ser incorrecta sin la lista exacta de features."
        )
except Exception as e:
    print(
        f"ERROR al cargar las columnas de features desde {FEATURE_COLUMNS_PATH}: {e}. La predicción podría ser incorrecta."
    )
    expected_feature_columns = None


# --- REPLICACIÓN DE FUNCIONES DE PREPROCESAMIENTO DEL CUADERNO ---


# Normalizador
def normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = (
        unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    )
    return texto.strip()


# 1. Construir vocabulario único (adaptado para una sola cadena de entrada)
def obtener_terminos_unicos_de_string(text_data: str) -> List[str]:
    vocab = set()
    if pd.isnull(text_data) or text_data.strip() == "":
        return []
    for item in str(text_data).split(","):
        vocab.add(normalizar(item))
    return list(vocab)


# 2. Precalcular matches (usamos el mismo del cuaderno)
def precalcular_diccionario(
    vocabulario: List[str], etiquetas_set: set, threshold: int = 70
) -> Dict[str, str]:
    diccionario_match = {}
    for termino in vocabulario:
        result = process.extractOne(
            termino, list(etiquetas_set), score_cutoff=threshold
        )  # labels es un set, lo convertimos a list
        if result:
            match, score, _ = result
            diccionario_match[termino] = match
    return diccionario_match


# 3. Aplicar mapeo usando el diccionario (igual al del cuaderno)
def estandarizar_entrada(
    texto: Optional[str], diccionario: Dict[str, str]
) -> List[str]:
    if pd.isnull(texto) or texto.strip() == "":
        return ["Desconocido"]  # Usamos "Desconocido" como en el cuaderno
    etiquetas_detectadas = set()
    for item in str(texto).split(","):
        item_norm = normalizar(item)
        etiquetas_detectadas.add(diccionario.get(item_norm, "Desconocido"))
    return list(etiquetas_detectadas)


# --- REPLICACIÓN DE LAS ETIQUETAS DEL CUADERNO ---
# Estas son tus categorías predefinidas



# --- FUNCIÓN CRÍTICA: _transform_data_for_employability_model ---
def _transform_data_for_employability_model(
    candidate_data: CandidateData,
) -> List[float]:
    """
    Transforma CandidateData (viniendo del front) en el vector de características
    que espera el modelo supervisado, usando los valores explícitos cuando existen
    y aplicando defaults solo como respaldo.
    """

    # --- Construir data_row con valores REALES del candidato ---

    sexo = candidate_data.gender or (
        # fallback mínimo si no viene gender
        "m"
        if candidate_data.name and candidate_data.name.lower().split()[-1].endswith("a")
        else "h"
    )

    edad = candidate_data.age if candidate_data.age is not None else 30
    estado_civil = candidate_data.maritalStatus or (
        "soltero" if "soltero" in (candidate_data.summary or "").lower() else "otro"
    )
    pais_nacimiento = candidate_data.birthCountry or "desconocido"
    num_idiomas = (
        candidate_data.numLanguages
        if candidate_data.numLanguages is not None
        else (len(candidate_data.languages) if candidate_data.languages else 0)
    )

    coche_propio = candidate_data.hasCar if candidate_data.hasCar is not None else False
    antecedentes_penales = (
        candidate_data.criminalRecord
        if candidate_data.criminalRecord is not None
        else True
    )
    orden_alejamiento = (
        candidate_data.restrainingOrder
        if candidate_data.restrainingOrder is not None
        else False
    )
    num_hijos = (
        candidate_data.numChildren if candidate_data.numChildren is not None else 0
    )
    incapacidad_laboral = (
        candidate_data.workDisability
        if candidate_data.workDisability is not None
        else False
    )
    minusvalia = (
        candidate_data.disabilityFlag
        if candidate_data.disabilityFlag is not None
        else False
    )
    demandante_empleo = (
        candidate_data.jobSeeker if candidate_data.jobSeeker is not None else True
    )

    experiencia_laboral = (
        ", ".join([exp.title for exp in candidate_data.experience])
        if candidate_data.experience
        else ""
    )
    cualidades = ", ".join(candidate_data.skills) if candidate_data.skills else ""
    puntos_debiles = candidate_data.weaknesses or ""
    formacion_candidato = (
        candidate_data.trainingProfile
        if candidate_data.trainingProfile
        else ", ".join([edu.degree for edu in candidate_data.education])
        if candidate_data.education
        else ""
    )

    data_row: Dict[str, Any] = {
        "Id_Candidato": candidate_data.id,
        "Sexo": sexo,
        "Edad": edad,
        "Estado_Civil": estado_civil,
        "Pais_Nacimiento": pais_nacimiento,
        "Num_Idiomas": num_idiomas,
        "Coche_Propio": coche_propio,
        "Antecedentes_Penales": antecedentes_penales,
        "Orden_Alejamiento": orden_alejamiento,
        "Num_hijos": num_hijos,
        "Incapacidad_Laboral": incapacidad_laboral,
        "Minusvalia": minusvalia,
        "Demandante_Empleo": demandante_empleo,
        "Experiencia_laboral": experiencia_laboral,
        "Cualidades": cualidades,
        "Puntos_Debiles": puntos_debiles,
        "Formación_candidato": formacion_candidato,
    }

    # Convertir a Series para aplicar lógica de pandas más fácil
    df_single = pd.Series(data_row).to_frame().T

    # --- PREPARANDO COLUMNAS SIMPLES (replicando el cuaderno) ---
    df_single["Is_women"] = df_single["Sexo"].apply(
        lambda x: str(x).strip().lower() == "m"
    )
    df_single["Es_Soltero"] = df_single["Estado_Civil"].apply(
        lambda x: str(x).strip().lower() == "soltero"
    )
    df_single["Hijos"] = df_single["Num_hijos"].apply(lambda x: x != 0)
    df_single["Origen_España"] = df_single["Pais_Nacimiento"].apply(
        lambda x: x.lower() == "españa"
    )

    # Convertir los booleanos directamente
    df_single["Coche_Propio"] = bool(
        df_single["Coche_Propio"].iloc[0]
    )  # .iloc[0] para acceder al valor
    df_single["Antecedentes_Penales"] = bool(df_single["Antecedentes_Penales"].iloc[0])
    df_single["Orden_Alejamiento"] = bool(df_single["Orden_Alejamiento"].iloc[0])
    df_single["Incapacidad_Laboral"] = bool(df_single["Incapacidad_Laboral"].iloc[0])
    df_single["Minusvalia"] = bool(df_single["Minusvalia"].iloc[0])
    df_single["Demandante_Empleo"] = bool(df_single["Demandante_Empleo"].iloc[0])

    # --- PREPARANDO COLUMNAS COMPLEJAS (MultiLabelBinarizer) ---
    df_encoded_parts = []

    for column, labels_set in etiquetas.items():
        # Generar vocabulario del dato de entrada (solo la fila actual)
        # Esto es diferente al cuaderno, ya que aquí no tenemos un DF completo
        input_text_for_column = df_single[column].iloc[
            0
        ]  # Obtener el string para esta columna
        vocabulario_input = obtener_terminos_unicos_de_string(input_text_for_column)

        diccionario_match = precalcular_diccionario(vocabulario_input, labels_set)

        # Aplicar estandarización para esta columna y esta fila
        new_column_data = estandarizar_entrada(input_text_for_column, diccionario_match)

        # Necesitamos un MultiLabelBinarizer por cada tipo de etiqueta para que sea consistente
        # Lo ideal es que estos MLB se guarden durante el entrenamiento y se carguen.
        # Por ahora, vamos a crear uno que ajusta a las etiquetas del diccionario.
        # ADVERTENCIA: Si las etiquetas reales del dataset son más amplias, este MLB podría no tener todas.
        mlb = MultiLabelBinarizer()

        # mlb necesita ser fitteado con todas las clases posibles que se vieron en el entrenamiento.
        # Si no lo guardamos y cargamos, debemos fittear con el set completo de etiquetas.
        mlb.fit(
            [list(labels_set)]
        )  # Fittear con el set completo de etiquetas para asegurar todas las columnas

        one_hot = mlb.transform([new_column_data])  # Transformar solo la fila actual

        df_encoded_part = pd.DataFrame(
            one_hot, columns=mlb.classes_, index=[df_single.index[0]]
        )
        sufijo = f"{column}_norm"  # Replicar el sufijo
        df_encoded_part.columns = [f"{sufijo}_{label}" for label in mlb.classes_]
        df_encoded_part = df_encoded_part.astype(bool)

        # Replicar la lógica de 'Desconocido'
        desconocido_col_name = f"{sufijo}_Desconocido"
        if desconocido_col_name in df_encoded_part.columns:
            # Asegúrate de que df_encoded_part.columns tiene otras etiquetas además de desconocido
            other_labels_exist = any(
                col for col in df_encoded_part.columns if col != desconocido_col_name
            )
            if other_labels_exist:
                # Si 'Desconocido' es True y hay otras etiquetas, Desconocido pasa a False.
                # Esto requiere saber qué otras etiquetas son.
                # La forma más segura es solo marcar Desconocido como True si es la única etiqueta.
                df_encoded_part[desconocido_col_name] = df_encoded_part.apply(
                    lambda row: row[desconocido_col_name]
                    and not any(
                        row[label]
                        for label in df_encoded_part.columns
                        if label != desconocido_col_name
                    ),
                    axis=1,
                )

        df_encoded_parts.append(df_encoded_part)

    df_enhanced_single = pd.concat(df_encoded_parts, axis=1)

    # --- Juntar todo y seleccionar las columnas finales ---
    # Eliminar columnas originales no usadas y el Id_Candidato
    final_df_processed = df_single.drop(
        columns=[
            "Id_Candidato",
            "Sexo",
            "Estado_Civil",
            "Pais_Nacimiento",
            "Num_hijos",
            "Experiencia_laboral",
            "Cualidades",
            "Puntos_Debiles",
            "Formación_candidato",
        ]
    )

    # Concatenar con las columnas MultiLabelBinarizer
    final_df_processed = pd.concat([final_df_processed, df_enhanced_single], axis=1)

    # Convertir Num_Idiomas y Edad a tipo numérico si no lo son
    final_df_processed["Num_Idiomas"] = pd.to_numeric(
        final_df_processed["Num_Idiomas"], errors="coerce"
    ).fillna(1)
    final_df_processed["Edad"] = pd.to_numeric(
        final_df_processed["Edad"], errors="coerce"
    ).fillna(30)  # Fillna con un valor sensato

    # Asegurar que todas las columnas booleanas sean del tipo correcto
    bool_cols = final_df_processed.select_dtypes(include="bool").columns
    for col in bool_cols:
        final_df_processed[col] = final_df_processed[col].astype(bool)

    # --- Selección final de características ---
    if expected_feature_columns:
        # Asegurarse de que todas las columnas esperadas existan.
        # Si una columna no existe, se añade con valor False (o 0 si no es booleana)
        missing_cols = set(expected_feature_columns) - set(final_df_processed.columns)
        for c in missing_cols:
            if "norm_" in c:  # Si es una columna de One-Hot, asumimos False
                final_df_processed[c] = False
            else:  # Para otras columnas numéricas, asumir 0 o un valor medio
                final_df_processed[c] = 0

        # Eliminar columnas que no están en expected_feature_columns
        extra_cols = set(final_df_processed.columns) - set(expected_feature_columns)
        final_df_processed = final_df_processed.drop(columns=list(extra_cols))

        # Reordenar las columnas al orden exacto esperado por el modelo
        model_input = final_df_processed[expected_feature_columns]
    else:
        # Si no se cargaron las columnas esperadas, hacemos un fallback simple (¡peligroso!)
        print(
            "ADVERTENCIA: No se pudieron cargar las columnas de features. Intentando usar las características generadas (la predicción podría ser incorrecta)."
        )
        model_input = final_df_processed

    # Devolver la primera (y única) fila de features como una lista
    return model_input.iloc[0].tolist()


# --- Función predict_employability (sin cambios en la lógica de predicción si ya estaba bien) ---
async def predict_employability(candidate_data: CandidateData) -> Dict[str, Any]:
    """
    Predice el score de empleabilidad y sugiere áreas de desarrollo.
    """
    model_features = _transform_data_for_employability_model(candidate_data)

    score: float

    if (
        employability_model
        and expected_feature_columns
        and len(model_features) == len(expected_feature_columns)
    ):
        try:
            if hasattr(employability_model, "predict_proba"):
                score = float(employability_model.predict_proba([model_features])[0][1])
            elif hasattr(employability_model, "predict"):
                score = float(employability_model.predict([model_features])[0])
            else:
                raise ValueError(
                    "Modelo cargado no tiene métodos predict_proba o predict."
                )

            score = max(0.0, min(1.0, score))

        except Exception as e:
            print(
                f"ERROR durante la predicción del modelo de empleabilidad: {e}. Usando simulación de score."
            )
            score = 0.5  # Fallback a un score neutral si falla

    else:
        print(
            "ADVERTENCIA: Modelo o features no disponibles/incorrectos. Usando simulación de score."
        )
        score = 0.5  # Fallback a un score neutral

    # --- Generación de áreas de desarrollo (puedes hacer esto más sofisticado) ---
    # Estas reglas ahora pueden ser más contextuales al score y a los datos de entrada
    areas_for_development = []

    # Reglas basadas en el score
    if score < 0.3:
        areas_for_development.append(
            "Necesita una fuerte orientación vocacional y formación básica."
        )
    elif score < 0.6:
        areas_for_development.append(
            "Fortalecer habilidades específicas y buscar mentoría."
        )

    if not candidate_data.experience:  # Si no hay experiencia
        areas_for_development.append(
            "Adquirir experiencia laboral a través de pasantías, voluntariado o prácticas."
        )
    if not candidate_data.education:  # Si no hay educación
        areas_for_development.append(
            "Considerar formación académica o cursos técnicos para mejorar el perfil."
        )
    if not any(
        s in candidate_data.skills
        for s in ["Comunicación", "Trabajo en equipo", "Liderazgo"]
    ):
        areas_for_development.append(
            "Desarrollar habilidades blandas (comunicación, trabajo en equipo, liderazgo)."
        )
    if (
        not areas_for_development
    ):  # Si no se detectaron áreas, dar una sugerencia general
        areas_for_development.append(
            "Continuar el desarrollo de habilidades y exploración de nuevas oportunidades."
        )

    return {
        "employability_score": round(score, 2),
        "areas_for_development": areas_for_development,
    }

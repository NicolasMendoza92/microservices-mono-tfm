import os

# import fitz
import pdfplumber
from docx import Document
from transformers import pipeline
from typing import List, Optional, Dict, Any
import re
from functools import lru_cache 
import logging
from schemas.cv import ExtractedCVData, ExperienceItem, EducationItem, LanguageItem
from utils.auxiliar import (
    parse_dates,
    normalize_job_title,
    categorize_education_level,
    DATE_RANGE_PATTERN,
    DATE_SINGLE_POINT_PATTERN,
)
from utils.index import (
    words_to_remove,
    common_skills_keywords,
    language_names,
    language_levels,
    summary_section_keywords,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Cargar el modelo de Hugging Face para NER ---
MODELO_PESADO = "dccuchile/bert-base-spanish-wwm-uncased-finetuned-ner"
NER_MODEL_NAME = "mrm8488/TinyBERT-spanish-uncased-finetuned-ner"
# ner_pipeline = pipeline(
#     "ner", model=NER_MODEL_NAME, tokenizer=NER_MODEL_NAME, aggregation_strategy="simple"
# )

# --- LAZY LOADER: solo se carga en el PRIMER request ---
@lru_cache(maxsize=1)  # ← Caché para cargar UNA SOLA VEZ
def get_ner_pipeline():
    """Lazy loader del modelo NER - se carga solo en el primer uso"""
    logger.info("🔄 Cargando modelo NER por primera vez...")
    ner_pipeline = pipeline(
        "ner", 
        model=NER_MODEL_NAME, 
        tokenizer=NER_MODEL_NAME, 
        aggregation_strategy="simple"
    )
    logger.info("✅ Modelo NER cargado exitosamente")
    return ner_pipeline


# --- Funciones de extracción de texto (sin cambios si ya funcionan bien) ---
async def extract_text_from_file(file_path: str) -> str:
    """Extrae texto de un archivo PDF, DOCX o TXT."""
    file_extension = os.path.splitext(file_path)[1].lower()
    text = ""

    if file_extension == ".pdf":
        try:
            with pdfplumber.open(file_path) as pdf:  
                for page in pdf.pages:
                    text += page.extract_text() or ""  
        except Exception as e:
            logger.error(f"Error al leer PDF {file_path}: {e}")
            raise ValueError("No se pudo extraer texto del PDF.")
    elif file_extension == ".docx":
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            logger.error(f"Error al leer DOCX {file_path}: {e}")
            raise ValueError("No se pudo extraer texto del DOCX.")
    elif file_extension == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        raise ValueError(f"Formato de archivo no soportado: {file_extension}")

    return text


# --- Nuevas funciones para la extracción modular ---
def extract_name(
    raw_text: str, file_name: str, ner_results: List[Dict[str, Any]]
) -> Optional[str]:
    name: Optional[str] = None
    
    # 0. PRIORIDAD ABSOLUTA: "NOMBRE:"
    explicit_name_match = re.search(
        r"(?i)\bnombre\s*:\s*([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]{5,})",
        raw_text
    )
    if explicit_name_match:
        candidate = explicit_name_match.group(1).strip()
        if 2 <= len(candidate.split()) <= 5:
            return candidate.title()

    # 1. Prioridad: Primeras líneas del documento con regex
    first_lines = raw_text.split("\n")[:5]
    if first_lines:
        name_match = re.search(
            r"^\s*([A-ZÁÉÍÓÚÄËÏÖÜÑ][a-záéíóúäëïöüñ]+\s+[A-ZÁÉÍÓÚÄËÏÖÜÑ][a-záéíóúäëïöüñ]+(?:(?:\s+de\s+|\s+del\s+|\s+y\s+|\s+)\s*[A-ZÁÉÍÓÚÄËÏÖÜÑ][a-záéíóúäëïöüñ]+)*)\s*$",
            first_lines[0],
            re.MULTILINE,
        )
        if name_match:
            candidate_name = name_match.group(1).strip()
            if 2 <= len(candidate_name.split()) <= 4:
                name = candidate_name

    # 2. Si no se encontró por regex, usa NER de los primeros segmentos
    if not name:
        person_entities = [
            ent["word"] for ent in ner_results if ent["entity_group"] == "PER"
        ]
        for ent in person_entities:
            if 2 <= len(ent.split()) <= 4 and raw_text.find(ent) < 500:
                name = ent.title()
                break
        if not name and person_entities:
            name = person_entities[0].title()

    # 3. Fallback: Intentar deducir del nombre del archivo
    if not name:
        filename = os.path.splitext(os.path.basename(file_name))[0].lower()
        filename_clean = re.sub(
            r"_(cv|curriculum|resume|ok|final|ult|version|v\d+|doc|file)$", "", filename
        )
        filename_clean = re.sub(
            r"-(cv|curriculum|resume|ok|final|ult|version|v\d+|doc|file)$",
            "",
            filename_clean,
        )

        words = filename_clean.split()
        cleaned_words = []
        for word in words:
            if word not in words_to_remove and len(word) > 1:
                cleaned_words.append(word.title())

        if len(cleaned_words) >= 2:
            name = " ".join(cleaned_words[:4])
        elif len(cleaned_words) == 1 and len(cleaned_words[0]) > 2:
            name = cleaned_words[0]

    return name


def extract_email(raw_text: str) -> Optional[str]:
    email_match = re.search(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", raw_text
    )
    if email_match:
        return email_match.group(0)
    return None


def extract_phone(raw_text: str) -> Optional[str]:
    explicit = re.search(
        r"(?i)\btel[eé]fono\s*:\s*([\d\s+-]{7,})",
        raw_text
    )
    if explicit:
        return re.sub(r"\D", "", explicit.group(1))

    generic = re.search(
        r"(\+?\d{1,3})?\s?\d{3}\s?\d{3}\s?\d{3}",
        raw_text
    )
    return re.sub(r"\D", "", generic.group(0)) if generic else None


def extract_skills(raw_text: str) -> List[str]:
    detected_skills = []
    for skill_keyword in common_skills_keywords:
        if re.search(r"\b" + re.escape(skill_keyword) + r"\b", raw_text, re.IGNORECASE):
            detected_skills.append(skill_keyword)
    return list(set(detected_skills))

def extract_experience(raw_text: str) -> List[ExperienceItem]:
    simplified_experience: List[ExperienceItem] = []

    sections_pattern = (
        r"(?i)(experiencia laboral|experiencia profesional|work experience)"
    )
    sections = re.split(sections_pattern, raw_text)

    experience_content = ""
    for i in range(len(sections)):
        section_part = sections[i].strip()
        if re.search(sections_pattern, section_part, re.IGNORECASE):
            if i + 1 < len(sections):
                experience_content += sections[i + 1].strip() + "\n"

    if experience_content:
        experience_entries = re.findall(
            rf"([^\n]+)\n\s*([^\n]+)\n\s*({DATE_RANGE_PATTERN}|{DATE_SINGLE_POINT_PATTERN}|presente|actualidad)\s*(?:[\n\s](.*))?",
            experience_content,
            re.IGNORECASE | re.DOTALL | re.VERBOSE,
        )

        for entry in experience_entries:
            title_raw = entry[0]
            dates_raw = entry[2]

            simplified_title = normalize_job_title(title_raw.strip())

            start_year, end_year = parse_dates(dates_raw)
            years_worked = end_year - start_year if start_year and end_year else 0

            if simplified_title != "Otro" and years_worked >= 0:
                simplified_experience.append(
                    ExperienceItem(
                        title=simplified_title,
                        years=max(0, years_worked),
                        description="",
                    )
                )

    if not simplified_experience:
        experience_matches = re.findall(
            rf"(?i)(?P<title>[\w\s,.-]+)\s+en\s+(?P<company>[\w\s,.-]+)(?:\s+\(({DATE_RANGE_PATTERN}|{DATE_SINGLE_POINT_PATTERN}|\d+\s+años?)\))?",
            raw_text,
            re.VERBOSE,
        )
        for match in experience_matches:
            title_raw = match[0]
            dates_years_str = match[2] if len(match) > 2 else ""

            simplified_title = normalize_job_title(title_raw.strip())

            years = 0
            if dates_years_str:
                if "años" in dates_years_str.lower():
                    years = (
                        int(re.search(r"\d+", dates_years_str).group(0))
                        if re.search(r"\d+", dates_years_str)
                        else 0
                    )
                else:
                    start_year, end_year = parse_dates(dates_years_str)
                    years = end_year - start_year if start_year and end_year else 0

            if simplified_title != "Otro" and years >= 0:
                simplified_experience.append(
                    ExperienceItem(title=simplified_title, years=max(0, years))
                )

    return simplified_experience

def extract_education(raw_text: str) -> List[EducationItem]:
    categorized_education: List[EducationItem] = []

    sections_pattern = r"(?i)(educación|formación académica|education|formación)"
    sections = re.split(sections_pattern, raw_text)

    education_content = ""
    for i in range(len(sections)):
        section_part = sections[i].strip()
        if re.search(sections_pattern, section_part, re.IGNORECASE):
            if i + 1 < len(sections):
                education_content += (
                    sections[i + 1].strip() + "\n"
                )  # Acumula contenido de educación

    # Si encontramos contenido de educación por secciones, lo procesamos
    if education_content:
        education_entries = re.findall(
            rf"([^\n]+)\n\s*([^\n]+)\n\s*({DATE_RANGE_PATTERN}|{DATE_SINGLE_POINT_PATTERN})",
            education_content,
            re.IGNORECASE | re.VERBOSE,
        )
        for entry in education_entries:
            degree_raw = entry[0]
            dates_raw = entry[2]

            education_text_for_categorization = f"{degree_raw}"
            categorized_level = categorize_education_level(
                education_text_for_categorization
            )

            _, end_year = parse_dates(dates_raw)

            if categorized_level != "No especificado":
                categorized_education.append(
                    EducationItem(degree=categorized_level, year=end_year)
                )

    # Fallback si no se encontró educación por secciones o si el contenido está menos estructurado
    if not categorized_education:
        education_matches = re.findall(
            rf"(?i)(?P<degree>[\w\s,.-]+)(?:\s+(?:en|de))?\s+(?P<institution>[\w\s,.-]+)(?:\s+\(({DATE_SINGLE_POINT_PATTERN}))?",
            raw_text,
            re.VERBOSE,
        )
        for match in education_matches:
            degree_raw = match[0]
            year_str = match[2] if len(match) > 2 else ""

            education_text_for_categorization = f"{degree_raw}"
            categorized_level = categorize_education_level(
                education_text_for_categorization
            )

            year = int(year_str) if year_str else None

            if categorized_level != "No especificado":
                categorized_education.append(
                    EducationItem(degree=categorized_level, year=year)
                )

    return categorized_education


def extract_languages(raw_text: str) -> List[LanguageItem]:
    """Extrae idiomas y sus niveles del candidato."""
    languages: List[LanguageItem] = []

    # Usaremos un set para evitar duplicados y mantener un seguimiento de los idiomas ya detectados
    detected_languages = set()

    # Patrón más robusto para detectar (Idioma: Nivel) o (Nivel Idioma)
    for lang_name_raw in language_names:
        for level_raw in language_levels:
            # Intentar el patrón "Idioma (Nivel)" o "Idioma - Nivel"
            pattern1 = rf"\b{re.escape(lang_name_raw)}\s*(?:-|\(|\:)\s*{re.escape(level_raw)}\b"
            # Intentar el patrón "Nivel Idioma"
            pattern2 = rf"\b{re.escape(level_raw)}\s*{re.escape(lang_name_raw)}\b"

            if re.search(pattern1, raw_text, re.IGNORECASE) or re.search(
                pattern2, raw_text, re.IGNORECASE
            ):
                # Normalizar el nombre del idioma (ej. "spanish" a "Español")
                normalized_lang_name = lang_name_raw.capitalize()
                if normalized_lang_name.lower() == "spanish":
                    normalized_lang_name = "Español"
                if normalized_lang_name.lower() == "english":
                    normalized_lang_name = "Inglés"
                if normalized_lang_name.lower() == "french":
                    normalized_lang_name = "Francés"
                if normalized_lang_name.lower() == "german":
                    normalized_lang_name = "Alemán"
                if normalized_lang_name.lower() == "italian":
                    normalized_lang_name = "Italiano"
                if normalized_lang_name.lower() == "portuguese":
                    normalized_lang_name = "Portugués"
                if normalized_lang_name.lower() == "chinese":
                    normalized_lang_name = "Chino"
                if normalized_lang_name.lower() == "japanese":
                    normalized_lang_name = "Japonés"

                # Normalizar el nivel (ej. "bilingual" a "Bilingüe", "fluent" a "Fluido")
                normalized_level = level_raw.capitalize()
                if normalized_level.lower() == "bilingual":
                    normalized_level = "Bilingüe"
                if normalized_level.lower() == "conversational":
                    normalized_level = "Conversacional"
                if normalized_level.lower() == "professional":
                    normalized_level = "Profesional"
                if normalized_level.lower() == "fluido":
                    normalized_level = "Fluido"

                lang_tuple = (normalized_lang_name, normalized_level)
                if lang_tuple not in detected_languages:
                    languages.append(
                        LanguageItem(name=normalized_lang_name, level=normalized_level)
                    )
                    detected_languages.add(lang_tuple)
    return languages


def extract_summary(raw_text: str) -> Optional[str]:
    summary: Optional[str] = None

    section_start_keywords_regex = r"(?i)\b(?:experiencia laboral|experiencia profesional|work experience|educación|formación académica|education|habilidades|skills|idiomas|languages|contacto|contact)\b"

    # Dividir el texto por saltos de línea y limpiar espacios
    paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()]

    # --- Estrategia 1: Buscar en el bloque inicial del CV ---
    max_paragraphs_for_initial_summary = 10
    initial_text_block = "\n".join(paragraphs[:max_paragraphs_for_initial_summary])
    print(initial_text_block)

    # Buscar el primer gran bloque de texto que no sea una lista o título
    current_summary_candidate = []

    # Definir palabras clave para el resumen (puedes ajustar esta lista)
    summary_keywords_regex = (
        r"(?i)\b(?:" + "|".join(re.escape(k) for k in summary_section_keywords) + r")\b"
    )

    # 1.1 Intentar encontrar el resumen *después* de un título de resumen, pero *antes* de otra sección
    found_summary_header = False
    potential_summary_start_index = -1

    for i, p in enumerate(paragraphs):
        p_lower = p.lower()
        if (
            re.search(summary_keywords_regex, p_lower) and len(p.split()) < 10
        ):  # Si es un título de sección de resumen
            found_summary_header = True
            potential_summary_start_index = (
                i + 1
            )  # El resumen debería empezar en el siguiente párrafo
            logger.info(
                f"Found summary header: '{p}' at paragraph {i}. Potential summary starts at {potential_summary_start_index}"
            )
            continue

        if found_summary_header and i >= potential_summary_start_index:
            # Si hemos encontrado un título de resumen y estamos después de él
            if (
                re.search(section_start_keywords_regex, p_lower) and len(p.split()) < 10
            ):  # Es el inicio de OTRA sección
                logger.info(
                    f"Found other section header: '{p}' at paragraph {i}. Summary ends here."
                )
                break  # El resumen termina aquí, salimos del bucle

            # Si el párrafo es lo suficientemente largo y no parece una lista/título
            if len(p.split()) > 15 and not re.search(
                r"^\s*[-•*]\s*|\d+\.\s*", p.strip()
            ):
                current_summary_candidate.append(p.strip())
            elif (
                len(current_summary_candidate) > 0 and len(p.split()) > 5
            ):  # Párrafos un poco más cortos que continúen un resumen
                current_summary_candidate.append(p.strip())
            else:
                # Si el párrafo es muy corto o es una lista y ya teníamos algo, podría ser el fin
                if len(current_summary_candidate) > 0 and (
                    len(p.split()) < 10
                    or re.search(r"^\s*[-•*]\s*|\d+\.\s*", p.strip())
                ):
                    logger.info(
                        f"Short/list paragraph after summary: '{p}'. Stopping summary collection."
                    )
                    break

    if current_summary_candidate:
        summary = " ".join(current_summary_candidate).strip()
        # Asegurarse de que el resumen no es solo una palabra clave de sección
        if not re.fullmatch(summary_keywords_regex, summary.lower()):
            if (
                len(summary.split()) > 20
            ):  # Un resumen debe tener al menos 20 palabras para ser válido
                logger.info(f"Summary found after header: {summary[:100]}...")
                return summary

    # 1.2 Intentar encontrar el resumen en los PRIMEROS PÁRRAFOS, sin necesidad de un encabezado explícito
    # Esto es para casos como el de "PAULA ANDREA ALVIA VEGA"
    if not summary:
        initial_paragraphs_for_summary_hunt = []
        for p in paragraphs:
            # Si encontramos una palabra clave de otra sección, paramos
            if (
                re.search(section_start_keywords_regex, p.lower())
                and len(p.split()) < 10
            ):
                logger.info(
                    f"Early section header found: '{p}'. Stopping initial summary hunt."
                )
                break
            # Si el párrafo es un resumen potencial (largo, no es una lista/título)
            if len(p.split()) > 15 and not re.search(
                r"^\s*[-•*]\s*|\d+\.\s*|^\s*(\w+\s*){1,4}$", p.strip()
            ):
                initial_paragraphs_for_summary_hunt.append(p.strip())
            # Si es un párrafo un poco más corto, pero no ruido (como nombres, datos de contacto)
            elif (
                len(p.split()) > 5
                and len(initial_paragraphs_for_summary_hunt) > 0
                and not (
                    re.search(r"^\s*[-•*]\s*|\d+\.\s*", p.strip())
                    or re.match(r"^[A-ZÁÉÍÓÚÄËÏÖÜÑ\s.-]+$", p.strip())
                )
            ):  # Evitar nombres/direcciones
                initial_paragraphs_for_summary_hunt.append(p.strip())

            # Limitar la búsqueda a los primeros X párrafos reales para evitar capturar experiencia o educación temprana
            if (
                len(initial_paragraphs_for_summary_hunt) > 3 and i > 10
            ):  # No más de 3 párrafos de resumen al principio o muy lejos
                break

        if initial_paragraphs_for_summary_hunt:
            candidate_summary_text = " ".join(
                initial_paragraphs_for_summary_hunt
            ).strip()
            if (
                len(candidate_summary_text.split()) > 20
            ):  # Debe ser un resumen significativo
                # Filtro final para asegurar que no sea solo el nombre o contacto que quedó por ahí
                if not re.fullmatch(
                    r"^[A-ZÁÉÍÓÚÄËÏÖÜÑ\s.-]+$", candidate_summary_text
                ) and not re.search(
                    r"\d{7,}", candidate_summary_text
                ):  # No es un número de teléfono muy largo
                    summary = candidate_summary_text
                    logger.info(f"Summary found in initial block: {summary[:100]}...")
                    return summary

    # Si todavía no hay resumen, volvemos a una búsqueda más general (tu lógica original, pero mejorada)
    # Busca un bloque de texto que esté ANTES de una sección conocida
    if not summary:
        all_paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()]
        temp_summary_paragraphs = []

        # Iterar todos los párrafos, buscando el primer bloque "tipo resumen"
        for p in all_paragraphs:
            p_lower = p.lower()
            # Si encontramos una palabra clave de otra sección, el resumen debe estar antes
            if re.search(section_start_keywords_regex, p_lower) and len(p.split()) < 10:
                break  # Es el inicio de una nueva sección, el resumen potencial termina aquí.

            # Si el párrafo es lo suficientemente largo y no es una lista/título/etc.
            if len(p.split()) > 20 and not re.search(
                r"^\s*[-•*]\s*|\d+\.\s*", p.strip()
            ):
                temp_summary_paragraphs.append(p.strip())
            elif (
                len(temp_summary_paragraphs) > 0
                and len(p.split()) > 10
                and not re.search(r"^\s*[-•*]\s*|\d+\.\s*", p.strip())
            ):
                # Permite párrafos ligeramente más cortos si ya estamos acumulando un resumen
                temp_summary_paragraphs.append(p.strip())
            else:
                # Si encontramos un párrafo muy corto o tipo lista después de empezar a acumular
                # Esto podría indicar el fin del resumen y el inicio de otro tipo de contenido
                if len(temp_summary_paragraphs) > 0 and (
                    len(p.split()) < 10
                    or re.search(r"^\s*[-•*]\s*|\d+\.\s*", p.strip())
                ):
                    break  # Detenemos la recolección

        if temp_summary_paragraphs:
            candidate_summary_text = " ".join(temp_summary_paragraphs).strip()
            if len(candidate_summary_text.split()) > 20:
                summary = candidate_summary_text
                logger.info(f"Summary found in general scan: {summary[:100]}...")

    # Un último fallback si no se encontró nada por los métodos anteriores
    if not summary:
        # Intenta coger el primer párrafo "largo" que no sea un título o lista
        for p in paragraphs:
            if len(p.split()) > 25 and not re.search(
                r"^\s*[-•*]\s*|\d+\.\s*|^\s*(\w+\s*){1,4}$", p.strip()
            ):
                summary = p.strip()
                logger.info(
                    f"Fallback summary found (first long paragraph): {summary[:100]}..."
                )
                break

    return summary


# --- Función principal de orquestación ---
async def extract_cv_data_from_text(
    raw_text: str, file_id: str, file_name: str
) -> ExtractedCVData:
    # logger.info("--- RAW TEXT ---")
    # logger.info(raw_text)

    clean_text = re.sub(r"\s*\n\s*", "\n", raw_text.strip())
    clean_text = re.sub(r"[ \t]+", " ", clean_text)
    logger.info(f"TEXTO LIMPIO (primeros 500 chars): \n {clean_text}")

    ner_pipeline = get_ner_pipeline()
    ner_results = ner_pipeline(clean_text)

    # Llamadas a las funciones modulares
    name = extract_name(clean_text, file_name, ner_results)
    email = extract_email(clean_text)
    phone = extract_phone(clean_text)
    skills = extract_skills(clean_text)

    # ¡Ahora llamamos a las funciones separadas!
    experience = extract_experience(clean_text)
    education = extract_education(clean_text)

    languages = extract_languages(clean_text)
    summary = extract_summary(clean_text)

    # Construir el objeto ExtractedCVData
    extracted_data = ExtractedCVData(
        name=name,
        email=email,
        phone=phone,
        skills=skills,
        experience=experience,
        education=education,
        languages=languages,
        summary=summary,
        raw_text=raw_text,
    )

    return extracted_data

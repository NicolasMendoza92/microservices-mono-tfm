
from typing import  Tuple 
import re
import datetime
from utils.standard_job_titles import STANDARD_JOB_TITLES
from utils.standard_education_levels import STANDARD_EDUCATION_LEVELS

MONTHS = [
    "enero", "ene", "febrero", "feb", "marzo", "mar", "abril", "abr", "mayo", "may",
    "junio", "jun", "julio", "jul", "agosto", "ago", "septiembre", "sep", "setiembre", "octubre", "oct",
    "noviembre", "nov", "diciembre", "dic"
]

MONTHS_PATTERN = r"(?:{})\.?".format("|".join(MONTHS))

DATE_SINGLE_POINT_PATTERN = rf"""
    (?P<month>{MONTHS_PATTERN})\s+(?P<year>\d{{4}})        # Mes con texto + año
    |
    (?P<month_num>\d{{1,2}})/(?P<year_num>\d{{4}})         # Mes numérico + año, ej: 12/2023
    |
    (?P<year_only>\d{{4}})                                 # Solo año
    |
    (?P<presente>presente|actualidad|hoy)                  # Presente
"""

DATE_RANGE_PATTERN = rf"""
    (?P<start>
        {MONTHS_PATTERN}\s+\d{{4}}                          # Mes texto + año inicio
        |
        \d{{1,2}}/\d{{4}}                                   # Mes numérico + año inicio
        |
        \d{{4}}                                             # Año inicio
    )
    \s*[-–—]\s*                                            # Separador - o similar
    (?P<end>
        {MONTHS_PATTERN}\s+\d{{4}}                          # Mes texto + año fin
        |
        \d{{1,2}}/\d{{4}}                                   # Mes numérico + año fin
        |
        \d{{4}}                                             # Año fin
        |
        presente|actualidad|hoy                              # Palabras para actualidad
    )
"""

DATE_SINGLE_POINT_REGEX = re.compile(DATE_SINGLE_POINT_PATTERN, re.VERBOSE | re.IGNORECASE)
DATE_RANGE_REGEX = re.compile(DATE_RANGE_PATTERN, re.VERBOSE | re.IGNORECASE)

def parse_dates(date_str: str) -> Tuple[int | None, int | None]:
    date_str = date_str.strip().lower()
    current_year = datetime.datetime.now().year

    # Primer intento: buscar un rango de fechas
    range_match = DATE_RANGE_REGEX.search(date_str)
    if range_match:
        start_str = range_match.group("start")
        end_str = range_match.group("end")

        start_year = None
        end_year = None

        # Función interna para extraer año de una fecha parcial
        def extract_year(s: str) -> int | None:
            s = s.lower().strip()
            # Intentar extraer año con regex de punto único
            sp_match = DATE_SINGLE_POINT_REGEX.search(s)
            if sp_match:
                if sp_match.group("year"):
                    return int(sp_match.group("year"))
                if sp_match.group("year_only"):
                    return int(sp_match.group("year_only"))
                if sp_match.group("presente"):
                    return current_year
            # Si no se detecta año válido, retornar None
            return None

        start_year = extract_year(start_str)
        if end_str in ["presente", "actualidad", "hoy"]:
            end_year = current_year
        else:
            end_year = extract_year(end_str)

        return start_year, end_year

    # Segundo intento: buscar una fecha simple puntual
    single_match = DATE_SINGLE_POINT_REGEX.search(date_str)
    if single_match:
        if single_match.group("year"):
            year = int(single_match.group("year"))
            return year, year
        if single_match.group("year_only"):
            year = int(single_match.group("year_only"))
            return year, year
        if single_match.group("presente"):
            return current_year, current_year

    # Si no se encontró fecha alguna, retornar None, None
    return None, None


def normalize_job_title(title: str) -> str:
    title_lower = title.lower()
    for standard_title, variations in STANDARD_JOB_TITLES.items():
        if title_lower == standard_title or any(re.search(r'\b' + re.escape(var) + r'\b', title_lower) for var in variations):
            return standard_title.title() 
    return "Otro" 


def categorize_education_level(text: str) -> str:
    text_lower = text.lower()

    # Primero verificamos los niveles más específicos o "altos"
    if any(re.search(r'\b' + re.escape(keyword) + r'\b', text_lower) for keyword in STANDARD_EDUCATION_LEVELS["Universitaria"]):
        return "Universitaria"
    if any(re.search(r'\b' + re.escape(keyword) + r'\b', text_lower) for keyword in STANDARD_EDUCATION_LEVELS["Formación Profesional"]):
        return "Formación Profesional"
    if any(re.search(r'\b' + re.escape(keyword) + r'\b', text_lower) for keyword in STANDARD_EDUCATION_LEVELS["Bachillerato"]):
        return "Bachillerato"
    if any(re.search(r'\b' + re.escape(keyword) + r'\b', text_lower) for keyword in STANDARD_EDUCATION_LEVELS["ESO/Secundaria"]):
        return "ESO/Secundaria"
    
    # Después, verificamos los cursos y certificaciones, que pueden ser complementarios a otros niveles
    if any(re.search(r'\b' + re.escape(keyword) + r'\b', text_lower) for keyword in STANDARD_EDUCATION_LEVELS["Curso/Certificación"]):
        return "Curso/Certificación"
        
    # Finalmente, si no se encuentra nada específico, se asume un nivel básico o no especificado
    if any(re.search(r'\b' + re.escape(keyword) + r'\b', text_lower) for keyword in STANDARD_EDUCATION_LEVELS["Sin formación específica"]):
        return "Sin formación específica"

    # Si no se categoriza con ninguna palabra clave, un valor por defecto.
    return "No especificado"

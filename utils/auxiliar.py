
from typing import List, Optional, Tuple 
import re
import datetime

STANDARD_JOB_TITLES = {
    "desarrollador de software": ["desarrollador", "programador", "ingeniero de software", "software engineer", "fullstack", "backend", "frontend"],
    "analista de datos": ["científico de datos", "data analyst", "data scientist", "especialista en datos"],
    "gerente de proyectos": ["project manager", "jefe de proyectos", "coordinador de proyectos"],
    "asistente administrativo": ["secretario", "auxiliar administrativo", "administrativo"],
    "operario de producción": ["operario", "obrero", "trabajador de fábrica", "producción"],
    "marketing y ventas": ["asesor comercial", "ejecutivo de ventas", "vendedor", "sales representative","marketing","comercial","promotor","vendedor"],
    "atención al cliente": ["call center", "soporte técnico", "servicio al cliente"],
    "contable": ["contabilidad", "auxiliar contable", "contable", "analista contable"],
    "logística": ["logístico", "operador logístico", "almacén", "inventario", "supply chain", "logística","almacén","operario","carretillero","inventario","supply chain","mozo"],
    "recursos humanos": ["rrhh", "gestor de talento", "recruitment", "seleccionador"],
    "hostelería": ["camarero","chef","cocinero","azafata","acomodador","maletero"],
    "salud": ["médico","enfermero","fisioterapeuta","farmacia","psicólogo","clínica","gerocultor"],
    "construcción": ["albañil","aparejador","arquitecto","fontanero","electricista","carpintero","pintor"],
    "educación": ["profesor","educador","formador","orientador","monitor"],
    "tecnología y diseño": ["informática","datos","multimedia","diseñador","diseño gráfico","ux/ui","autocad","solidworks","mantenimiento"],
    "construcción": ["albañil","aparejador","arquitecto","fontanero","electricista","carpintero","pintor"],
    "servicios": ["atención al cliente","recepcionista","secretaria","teleoperador","telemarketing"],
    "transporte": [ "conductor","mensajero","repartidor","transporte","grúa","parking"],
    "alimentación": ["alimentos","carnicero","charcutero","frutero","panadero","pescadero"],
    "seguridad": ["vigilante","seguridad","socorrista"],
    "hogar y limpieza": ["empleada hogar","limpiador","lavandería","planchador"],
    "jurídico": ["abogado","asesor jurídico","notario","procurador"],
    "otros": ["actor","acomodador","intérprete","traductor","funerario"]
}

MONTHS_ES = r'(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|\w{3}\.?)'
DATE_SINGLE_POINT_PATTERN = rf'(?:{MONTHS_ES}\s+)?\d{{4}}|presente|actualidad'
DATE_PATTERN = rf'(?:{DATE_SINGLE_POINT_PATTERN}\s*-\s*{DATE_SINGLE_POINT_PATTERN})|{DATE_SINGLE_POINT_PATTERN}'


def parse_dates(date_str: str) -> tuple[Optional[int], Optional[int]]:
    start_year, end_year = None, None
    current_year = datetime.datetime.now().year
    date_str_lower = date_str.lower()

    month_map = {
        'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12,
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
    }

    # Regex para capturar "Mes Año" o solo "Año"
    DATE_ENTRY_PATTERN = r'(?:(?:' + '|'.join(month_map.keys()) + r')\s+)?(\d{4}|presente|actualidad)'
    
    # Coincidencia para "Inicio - Fin"
    full_date_match = re.search(rf'({DATE_ENTRY_PATTERN})\s*-\s*({DATE_ENTRY_PATTERN})', date_str_lower, re.IGNORECASE)

    if full_date_match:
        start_part = full_date_match.group(1)
        end_part = full_date_match.group(3) # group(3) porque el segundo grupo es el año del inicio
        
        # Parsear inicio
        start_year_match = re.search(r'\d{4}', start_part)
        if start_year_match:
            start_year = int(start_year_match.group(0))

        # Parsear fin
        if "presente" in end_part or "actualidad" in end_part:
            end_year = current_year
        else:
            end_year_match = re.search(r'\d{4}', end_part)
            if end_year_match:
                end_year = int(end_year_match.group(0))
    else:
        # Coincidencia para un solo año o "Presente"
        single_year_match = re.search(r'(\d{4})', date_str)
        if single_year_match:
            start_year = int(single_year_match.group(1))
            end_year = start_year # Si solo hay un año, asumimos que es el fin y el inicio

        if "presente" in date_str_lower or "actualidad" in date_str_lower:
            end_year = current_year
            if start_year is None: # Si solo dice "presente" o "actualidad" sin año de inicio
                # Podríamos intentar encontrar un año anterior en el texto o dejarlo None
                pass 
    
    if start_year and not end_year and ("presente" in date_str_lower or "actualidad" in date_str_lower):
        end_year = current_year
    
    return start_year, end_year

def normalize_job_title(title: str) -> str:
    """Normaliza un título de trabajo a un estándar si encuentra una coincidencia."""
    title_lower = title.lower()
    for standard_title, variations in STANDARD_JOB_TITLES.items():
        if title_lower == standard_title or any(var in title_lower for var in variations):
            return standard_title.title() # Retorna el estándar capitalizado
    return title.title()
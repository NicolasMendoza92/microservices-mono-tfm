
from typing import List, Optional, tuple 
import re
import datetime
# ... el resto de tus importaciones ...

def parse_dates(date_str: str) -> tuple[Optional[int], Optional[int]]: # <-- CORRECCIÓN AQUÍ
    """
    Parsea una cadena de fechas (ej. '2018-2022', 'Enero 2020 - Actualidad', '2015')
    y retorna el año de inicio y el año de fin como una tupla.
    """
    start_year, end_year = None, None
    current_year = datetime.datetime.now().year

    date_str_lower = date_str.lower()

    if "presente" in date_str_lower or "actualidad" in date_str_lower:
        end_year = current_year

    # Coincidencia YYYY - YYYY
    match_range = re.search(r'(\d{4})\s*-\s*(\d{4})', date_str)
    if match_range:
        start_year = int(match_range.group(1))
        end_year = int(match_range.group(2))
    else:
        # Coincidencia YYYY (como único año o año de inicio/fin no especificado)
        years = re.findall(r'\d{4}', date_str)
        if len(years) == 2: # Ej. "Marzo 2018 - Enero 2022"
            start_year = int(years[0])
            end_year = int(years[1])
        elif len(years) == 1: # Un solo año
            year = int(years[0])
            if start_year is None: start_year = year # Si no hay inicio, es el inicio
            if end_year is None: end_year = year     # Si no hay fin, es el fin
        
    # Si 'actualidad' está presente pero el end_year no se capturó por regex
    if ("presente" in date_str_lower or "actualidad" in date_str_lower) and end_year is None:
        end_year = current_year

    # Si solo hay un año y es una fecha de inicio, y no hay 'presente', el fin es el mismo año
    if start_year and not end_year:
        end_year = start_year 
    
    # Calcular años de experiencia de manera simple, si ambos están
    # La tupla ya retorna los años, el cálculo de "años trabajados" se hará en la función llamante
    
    return start_year, end_year
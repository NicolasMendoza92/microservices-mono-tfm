# models/cv_processing.py

import os
import fitz # PyMuPDF para PDFs
from docx import Document # python-docx para .docx
from transformers import pipeline
from typing import List, Optional
import re
import datetime
from schemas.cv import ExtractedCVData, ExperienceItem, EducationItem, LanguageItem
from utils.dates_handler import parse_dates


# --- Cargar el modelo de Hugging Face para NER ---
NER_MODEL_NAME = "dccuchile/bert-base-spanish-wwm-uncased-finetuned-ner"
ner_pipeline = pipeline("ner", model=NER_MODEL_NAME, tokenizer=NER_MODEL_NAME, aggregation_strategy="simple")

# --- Funciones de extracción de texto (sin cambios si ya funcionan bien) ---
async def extract_text_from_file(file_path: str) -> str:
    file_extension = os.path.splitext(file_path)[1].lower()
    text = ""

    if file_extension == ".pdf":
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            print(f"Error al leer PDF {file_path}: {e}")
            raise ValueError("No se pudo extraer texto del PDF.")
    elif file_extension == ".docx":
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            print(f"Error al leer DOCX {file_path}: {e}")
            raise ValueError("No se pudo extraer texto del DOCX.")
    elif file_extension == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        raise ValueError(f"Formato de archivo no soportado: {file_extension}")

    return text

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

def normalize_job_title(title: str) -> str:
    """Normaliza un título de trabajo a un estándar si encuentra una coincidencia."""
    title_lower = title.lower()
    for standard_title, variations in STANDARD_JOB_TITLES.items():
        if title_lower == standard_title or any(var in title_lower for var in variations):
            return standard_title.title() # Retorna el estándar capitalizado
    return title.title()

async def extract_cv_data_from_text(raw_text: str, file_id: str) -> ExtractedCVData:

    ner_results = ner_pipeline(raw_text)

    # Inicializar con valores por defecto
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = []
    experience: List[ExperienceItem] = []
    education: List[EducationItem] = []
    languages: List[LanguageItem] = []
    summary: Optional[str] = None
    
    # Normalizar el texto para facilitar la detección de secciones
    normalized_text = raw_text.lower().replace('\n', ' ').replace('\r', ' ')

    # --- 1. Extracción de Nombre (Prioridad: Principio del documento, NER) ---
    # Intenta encontrar el nombre en las primeras líneas/párrafos
    first_lines = raw_text.split('\n')[:5] # Primeras 5 líneas
    if first_lines:
        # Intenta un regex para nombres comunes al inicio
        name_match = re.search(r'^\s*([A-ZÁÉÍÓÚÄËÏÖÜÑ][a-záéíóúäëïöüñ]+\s+[A-ZÁÉÍÓÚÄËÏÖÜÑ][a-záéíóúäëïöüñ]+(?:(?:\s+de\s+|\s+del\s+|\s+y\s+|\s+)\s*[A-ZÁÉÍÓÚÄËÏÖÜÑ][a-záéíóúäëïöüñ]+)*)\s*$', first_lines[0], re.MULTILINE)
        if name_match:
            name = name_match.group(1).strip()
            # Una heurística: si el nombre es muy corto o muy largo, descartar
            if len(name.split()) < 2 or len(name.split()) > 4:
                name = None
        
    # Si no se encontró por regex, usa NER de los primeros segmentos
    if not name:
        person_entities = [ent['word'] for ent in ner_results if ent['entity_group'] == 'PER']
        # Prioriza entidades PER que aparecen al principio del texto
        for ent in person_entities:
            # Asegura que sea un nombre coherente (ej: 2-4 palabras)
            if len(ent.split()) >= 2 and len(ent.split()) <= 4 and raw_text.find(ent) < 500: # Aparece al inicio del CV
                name = ent.title()
                break
        if not name and person_entities:
            name = person_entities[0].title() 
            
    # 2. Extracción de Email (regex)
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', raw_text)
    if email_match:
        email = email_match.group(0)

    # 3. Extracción de Teléfono (regex)
    phone_match = re.search(r'(\+?\d{1,4}[-.\s]?)?(\(?\d{2,}\)?[-.\s]?\d{3,4}[-.\s]?\d{4})', raw_text)
    if phone_match:
        phone = phone_match.group(0).strip()
        # Limpieza básica: quitar caracteres no numéricos excepto el '+' inicial
        phone = re.sub(r'[\s.-]', '', phone)
        if not phone.startswith('+'): # Si no es internacional, añade prefijo local si es necesario (ej. +34)
            pass

    # 4. Extracción de Habilidades (keywords, podría ser un modelo de clasificación o QA)
    common_skills_keywords = [
        "Python", "JavaScript", "React", "Node.js", "SQL", "Git", "Docker", "AWS", "Azure",
        "Machine Learning", "Data Analysis", "Comunicación", "Liderazgo", "Trabajo en equipo",
        "Resolución de problemas", "Excel", "Word", "PowerPoint", "Marketing Digital",
        "Ventas", "Atención al cliente", "Contabilidad", "Finanzas", "Java", "C++", "C#",
        "Scrum", "Agile", "Linux", "Windows Server", "Networking", "SEO", "SEM", "UX/UI",
        "Diseño Gráfico", "Autocad", "SolidWorks", "Mantenimiento", "Producción", "Logística",
        "Inventario", "SAP", "CRM", "Negociación", "Project Management", "Power BI", "Tableau",
        "trabajo en equipo", "responsabilidad", "puntualidad", "comunicación", "proactividad", "flexibilidad", "organización",
        "aprendizaje continuo", "adaptabilidad", "resolución de problemas", "liderazgo", "empatía", "iniciativa", "tolerancia al estrés",
        "resiliencia", "autonomía", "creatividad", "ética laboral", "orientación al cliente", "disciplina", "compromiso", "colaboración",
        "capacidad de análisis", "honestidad", "motivación"
    ]
    detected_skills = []
    for skill_keyword in common_skills_keywords:
        if re.search(r'\b' + re.escape(skill_keyword) + r'\b', raw_text, re.IGNORECASE):
            detected_skills.append(skill_keyword)
    skills = list(set(detected_skills)) # Eliminar duplicados
    
    # --- 5. Extracción de Experiencia Laboral y Educación (más estructurado por secciones) ---

    # Regex para fechas: YYYY, YYYY-YYYY, Mes YYYY - Mes YYYY, Actual
    DATE_PATTERN = r'(?:(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|\w{3}\.?)\s+\d{4}|presente|actualidad|\d{4})\s*-\s*(?:(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|\w{3}\.?)\s+\d{4}|presente|actualidad|\d{4})|\d{4}\s*-\s*\d{4}|\d{4}|presente|actualidad'
    
    # Marcadores de sección
    sections = re.split(r'(?i)(experiencia laboral|experiencia profesional|work experience|educación|formación académica|education)', raw_text)
    
    current_section = None
    for i, section_text in enumerate(sections):
        section_text_lower = section_text.lower().strip()
        if "experiencia laboral" in section_text_lower or "experiencia profesional" in section_text_lower or "work experience" in section_text_lower:
            current_section = "experience"
            continue
        elif "educación" in section_text_lower or "formación académica" in section_text_lower or "education" in section_text_lower:
            current_section = "education"
            continue
        
        if current_section == "experience":
            # Patrón más flexible: Título/Puesto, Empresa, Fechas (con responsabilidades opcionales)
            # Buscar cada entrada de experiencia como un bloque
            experience_entries = re.findall(
                rf'([^\n]+)\n\s*([^\n]+)\n\s*({DATE_PATTERN})\n((?:[^\n]*\n)*?)(?=\n[^\n]|\Z)', # Captura título, empresa, fechas, y posibles responsabilidades
                section_text, re.IGNORECASE
            )
            for entry in experience_entries:
                title_raw, company_raw, dates_raw, responsibilities = entry[0], entry[1], entry[2], entry[3]
                
                # Intentar limpiar y normalizar
                title = normalize_job_title(title_raw.strip())
                company = company_raw.strip().title()
                
                start_year, end_year = parse_dates(dates_raw) # Función auxiliar para parsear fechas
                years_worked = end_year - start_year if start_year and end_year else 0
                
                if len(title) > 3 and len(company) > 3: # Filtro básico de ruido
                    experience.append(ExperienceItem(
                        title=title,
                        company=company,
                        years=max(0, years_worked),
                        # Aquí podrías añadir un campo para 'description' si lo incluyes en tu schema
                        # description=responsibilities.strip()
                    ))
        
        elif current_section == "education":
            # Patrón para educación: Grado, Institución, Año
            education_entries = re.findall(
                rf'([^\n]+)\n\s*([^\n]+)\n\s*({DATE_PATTERN})(?=\n[^\n]|\Z)',
                section_text, re.IGNORECASE
            )
            for entry in education_entries:
                degree_raw, institution_raw, dates_raw = entry[0], entry[1], entry[2]
                
                degree = degree_raw.strip().title()
                institution = institution_raw.strip().title()
                
                # Usamos solo el año final o el único año presente
                _, end_year = parse_dates(dates_raw)
                
                if len(degree) > 3 and len(institution) > 3:
                    education.append(EducationItem(
                        degree=degree,
                        institution=institution,
                        year=end_year
                    ))
    
    # Fallback si no se encuentran secciones, usa el regex más simple que ya tenías (o refina el de arriba)
    if not experience: # Si la extracción por sección falla, intenta el patrón general
        experience_matches = re.findall(r'(?i)(?P<title>[A-ZÁÉÍÓÚ\s,\.-]+)\s+en\s+(?P<company>[A-ZÁÉÍÓÚ\s,\.-]+)(?:\s+\((\d{4}(?:\s*-\s*\d{4})?|\d+\s+años?))?\)?', raw_text)
        for match in experience_matches:
            title, company, years_str = match[0], match[1], match[2]
            years = 0
            if years_str:
                if "años" in years_str.lower():
                    years = int(re.search(r'\d+', years_str).group(0))
                elif "-" in years_str:
                    start_year, end_year = map(int, years_str.split('-'))
                    years = end_year - start_year
                else:
                    try: # Si es un solo año, asumimos que es el final
                        years = datetime.datetime.now().year - int(years_str)
                    except ValueError:
                        pass

        # Filtrar posibles ruidos, asegurar que no sean solo palabras comunes
        if len(title.strip()) > 5 and len(company.strip()) > 5:
             experience.append(ExperienceItem(title=title.strip(), company=company.strip(), years=max(0, years)))

    if not education: # Si la extracción por sección falla, intenta el patrón general
        education_matches = re.findall(r'(?i)(?P<degree>[A-ZÁÉÍÓÚ\s,\.-]+)(?:\s+(?:en|de))?\s+(?P<institution>[A-ZÁÉÍÓÚ\s,\.-]+)(?:\s+\((\d{4}))?\)?', raw_text)
        for match in education_matches:
            degree, institution, year_str = match[0], match[1], match[2]
            if year_str:
                year = int(year_str)
            else:
                year = None
            
            if len(degree.strip()) > 5 and len(institution.strip()) > 5:
                education.append(EducationItem(degree=degree.strip(), institution=institution.strip(), year=year))


    # # 5. Extracción de Experiencia Laboral y Educación
    # experience_matches = re.findall(r'(?i)(?P<title>[A-ZÁÉÍÓÚ\s,]+)\s+en\s+(?P<company>[A-ZÁÉÍÓÚ\s,]+)(?:\s+\((\d{4}(?:\s*-\s*\d{4})?|\d+\s+años?))\)?', raw_text)
    


    # # Educación
    # # Patrón simplificado: (Grado) de (Institución) (Año)
    # education_matches = re.findall(r'(?i)(?P<degree>[A-ZÁÉÍÓÚ\s,]+)(?:\s+(?:en|de))?\s+(?P<institution>[A-ZÁÉÍÓÚ\s,]+)(?:\s+\((\d{4}))\)?', raw_text)
    
    # 6. Extracción de Idiomas (keywords + nivel)
    # Podrías buscar patrones como "Idioma: Nivel" o "Nivel Idioma"
    language_levels = ["nativo", "avanzado", "intermedio", "básico", "fluido"]
    language_names = ["español", "inglés", "francés", "alemán", "italiano", "portugués", "chino", "japonés"]

    for lang_name in language_names:
        for level in language_levels:
            if re.search(r'\b' + re.escape(lang_name) + r'\b.*\b' + re.escape(level) + r'\b', raw_text, re.IGNORECASE):
                languages.append(LanguageItem(name=lang_name.capitalize(), level=level.capitalize()))
                break # Solo añadir una vez por idioma
            elif re.search(r'\b' + re.escape(level) + r'\b.*\b' + re.escape(lang_name) + r'\b', raw_text, re.IGNORECASE):
                 languages.append(LanguageItem(name=lang_name.capitalize(), level=level.capitalize()))
                 break

    # 7. Resumen Profesional (heurística, buscar una sección al inicio o después del nombre)
    # Esto es muy difícil sin un modelo específico. Para simular, podríamos tomar el primer párrafo largo.
    summary_section_keywords = ["resumen", "perfil profesional", "acerca de mí", "objetivo profesional", "summary", "profile"]
    summary_section_start = -1
    for keyword in summary_section_keywords:
        idx = normalized_text.find(keyword)
        if idx != -1:
            summary_section_start = idx
            break

    if summary_section_start != -1:
        # Tomar un segmento después del encabezado y buscar el primer párrafo significativo
        summary_text_segment = raw_text[summary_section_start:summary_section_start + 700] # Un poco más largo
        paragraphs = [p.strip() for p in summary_text_segment.split('\n') if p.strip()]
        for p in paragraphs:
            if len(p.split()) > 30 and not re.search(r'^\s*•|\d+\.\s*', p): # Más de 30 palabras
                summary = p
                break
    
    if not summary: # Fallback a tu lógica anterior si no se encuentra por sección
        paragraphs = [p.strip() for p in raw_text.split('\n') if p.strip()]
        if paragraphs:
            for p in paragraphs:
                if len(p.split()) > 20 and not re.search(r'^\s*•|\d+\.\s*', p):
                    summary = p
                    break
            if not summary and len(paragraphs[0].split()) > 10:
                summary = paragraphs[0]
    # paragraphs = [p.strip() for p in raw_text.split('\n') if p.strip()]
    # if paragraphs:
    #     # Intenta encontrar un párrafo largo que no sea una lista o info de contacto
    #     for p in paragraphs:
    #         if len(p.split()) > 20 and not re.search(r'^\s*•|\d+\.\s*', p): # Más de 20 palabras, no una lista
    #             summary = p
    #             break
    #     if not summary and len(paragraphs[0].split()) > 10: # Si no encuentra, usa el primer párrafo si es razonablemente largo
    #         summary = paragraphs[0]


    # Construir el objeto ExtractedCVData
    extracted_data = ExtractedCVData(
        id=file_id,
        name=name,
        email=email,
        phone=phone,
        skills=skills,
        experience=experience,
        education=education,
        languages=languages,
        summary=summary,
        raw_text=raw_text 
    )

    return extracted_data


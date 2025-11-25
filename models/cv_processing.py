# models/cv_processing.py

import os
import fitz # PyMuPDF para PDFs
from docx import Document # python-docx para .docx
from transformers import pipeline
from typing import List, Optional
import re
import datetime
from schemas.cv import ExtractedCVData, ExperienceItem, EducationItem, LanguageItem

# --- Cargar el modelo de Hugging Face para NER ---
# Usaremos un pipeline de token-classification (NER)
# Puedes buscar otros modelos en https://huggingface.co/models
# Por ejemplo, para español: 'dccuchile/bert-base-spanish-wwm-uncased-finetuned-ner'
# O un modelo más genérico si la información no es específica de personas/organizaciones: 'Davlan/bert-base-multilingual-cased-ner-hrb'
# O si tienes un dataset para fine-tune un modelo para CVs específicamente: 'JuanCervantes/bert-base-spanish-wwm-cased-finetuned-CV'
NER_MODEL_NAME = "dccuchile/bert-base-spanish-wwm-uncased-finetuned-ner"
ner_pipeline = pipeline("ner", model=NER_MODEL_NAME, tokenizer=NER_MODEL_NAME, aggregation_strategy="simple")

# --- Funciones de extracción de texto (sin cambios si ya funcionan bien) ---
async def extract_text_from_file(file_path: str) -> str:
    """Extrae texto de un CV (PDF o DOCX). Añade lógica para otros formatos."""
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


async def extract_cv_data_from_text(raw_text: str, file_id: str) -> ExtractedCVData:
    """
    Extrae y estructura los datos del CV utilizando NER de Hugging Face
    y heurísticas/regex.
    """
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

    # --- Lógica de extracción de información del CV ---
    # 1. Extracción de Nombre (usando NER)
    person_entities = [ent['word'] for ent in ner_results if ent['entity_group'] == 'PER']
    if person_entities:
        # Intenta unificar si el nombre está segmentado
        # Esto es muy básico, un enfoque más robusto podría usar el principio de adyacencia
        name = " ".join(person_entities[:3]) # Tomar las primeras 3 palabras como nombre, heurística
        name = name.title() # Capitalizar

    # 2. Extracción de Email (regex)
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', raw_text)
    if email_match:
        email = email_match.group(0)

    # 3. Extracción de Teléfono (regex)
    # Patrón más robusto para números de teléfono comunes en Latinoamérica/España
    phone_match = re.search(r'(\+?\d{1,4}[-.\s]?)?(\(?\d{2,}\)?[-.\s]?\d{3,4}[-.\s]?\d{4})', raw_text)
    if phone_match:
        phone = phone_match.group(0)

    # 4. Extracción de Habilidades (keywords, podría ser un modelo de clasificación o QA)
    # Lista de habilidades comunes para buscar (extiende esta lista)
    common_skills_keywords = [
        "Python", "JavaScript", "React", "Node.js", "SQL", "Git", "Docker", "AWS", "Azure",
        "Machine Learning", "Data Analysis", "Comunicación", "Liderazgo", "Trabajo en equipo",
        "Resolución de problemas", "Excel", "Word", "PowerPoint", "Marketing Digital",
        "Ventas", "Atención al cliente", "Contabilidad", "Finanzas", "Java", "C++", "C#",
        "Scrum", "Agile", "Linux", "Windows Server", "Networking", "SEO", "SEM", "UX/UI",
        "Diseño Gráfico", "Autocad", "SolidWorks", "Mantenimiento", "Producción", "Logística",
        "Inventario", "SAP", "CRM", "Negociación", "Project Management", "Power BI", "Tableau"
    ]
    detected_skills = []
    for skill_keyword in common_skills_keywords:
        if re.search(r'\b' + re.escape(skill_keyword) + r'\b', raw_text, re.IGNORECASE):
            detected_skills.append(skill_keyword)
    skills = list(set(detected_skills)) # Eliminar duplicados

    # 5. Extracción de Experiencia Laboral y Educación
    # Esta es la parte más compleja y a menudo requiere enfoques avanzados:
    # - Modelos de PLN específicos para CV parsing (fine-tuning)
    # - Reglas basadas en patrones (ej. buscar "Cargo en Empresa", "Fecha Inicio - Fecha Fin")
    # - Modelos de "span extraction" o "question answering"
    
    # Para la simulación, vamos a usar un enfoque basado en palabras clave y regex para demostrar:

    # Experiencia
    # Patrón simplificado: (Cargo) en (Empresa) (Fecha/años)
    experience_matches = re.findall(r'(?i)(?P<title>[A-ZÁÉÍÓÚ\s,]+)\s+en\s+(?P<company>[A-ZÁÉÍÓÚ\s,]+)(?:\s+\((\d{4}(?:\s*-\s*\d{4})?|\d+\s+años?))\)?', raw_text)
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


    # Educación
    # Patrón simplificado: (Grado) de (Institución) (Año)
    education_matches = re.findall(r'(?i)(?P<degree>[A-ZÁÉÍÓÚ\s,]+)(?:\s+(?:en|de))?\s+(?P<institution>[A-ZÁÉÍÓÚ\s,]+)(?:\s+\((\d{4}))\)?', raw_text)
    for match in education_matches:
        degree, institution, year_str = match[0], match[1], match[2]
        if year_str:
            year = int(year_str)
        else:
            year = None
        
        if len(degree.strip()) > 5 and len(institution.strip()) > 5:
            education.append(EducationItem(degree=degree.strip(), institution=institution.strip(), year=year))

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
    paragraphs = [p.strip() for p in raw_text.split('\n') if p.strip()]
    if paragraphs:
        # Intenta encontrar un párrafo largo que no sea una lista o info de contacto
        for p in paragraphs:
            if len(p.split()) > 20 and not re.search(r'^\s*•|\d+\.\s*', p): # Más de 20 palabras, no una lista
                summary = p
                break
        if not summary and len(paragraphs[0].split()) > 10: # Si no encuentra, usa el primer párrafo si es razonablemente largo
            summary = paragraphs[0]


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
        raw_text=raw_text # Guardar el raw_text para auditoría o uso posterior
    )

    return extracted_data

# --- Nueva función para procesar CV con Hugging Face NER ---
# async def process_cv_with_huggingface_ner(file_path: str) -> Dict[str, Any]:
#     """
#     Procesa un CV utilizando un modelo de Hugging Face para Extracción de Entidades Nombradas.
#     """
#     try:
#         raw_text = await extract_text_from_file(file_path)
#     except ValueError as e:
#         raise e # Re-lanza el error para que FastAPI lo capture

#     # Realizar la extracción de entidades nombradas
#     ner_results = ner_pipeline(raw_text)

#     # --- Lógica para estructurar los datos del CV a partir de los resultados de NER ---
#     # Esto es una parte CRÍTICA y a menudo requiere heurísticas y post-procesamiento.
#     # Los modelos de NER identifican categorías generales como PER (Persona), ORG (Organización), LOC (Lugar).
#     # Para CVs, necesitas extraer cosas más específicas como habilidades, experiencia, educación.

#     name = None
#     skills: List[str] = []
#     experience: List[Dict] = []
#     education: List[Dict] = []

#     # Ejemplo muy básico de procesamiento de resultados NER:
#     # Vas a necesitar una lógica más sofisticada aquí.
#     # NER suele dar entidades como 'PERSON', 'ORG', 'LOC'. No directamente 'skills' o 'years_experience'.
#     # Para habilidades, quizás necesites un enfoque de keyword matching o un modelo custom.

#     current_person_entities = []
#     for entity in ner_results:
#         if entity['entity_group'] == 'PER':
#             current_person_entities.append(entity['word'])
#         elif entity['entity_group'] == 'ORG':
#             # Podría ser una empresa o una institución educativa
#             pass # Lógica más compleja para diferenciar
#         # Otras entidades...

#     # Si hay entidades PERSON, tomar la primera como nombre (muy simplificado)
#     if current_person_entities:
#         name = " ".join(current_person_entities) # Juntar partes del nombre

#     # --- Simulación de extracción de habilidades, experiencia y educación ---
#     # Los modelos de NER generales no extraen esto directamente.
#     # Para esto, tendrías que:
#     # 1. Usar un modelo fine-tuned específicamente para CVs (si existe).
#     # 2. Implementar reglas o expresiones regulares sobre `raw_text` para patrones comunes.
#     # 3. Usar un enfoque de "zero-shot classification" o "question-answering" con un LLM si tienes descripciones de habilidades.

#     # POR AHORA, usaremos una mezcla de simulación y un intento muy básico de palabras clave
#     # para demostrar cómo empezar a poblar estos campos.

#     # Simulación de habilidades basadas en palabras clave (necesitarás un diccionario o un modelo más avanzado)
#     common_skills = ["Python", "JavaScript", "SQL", "Machine Learning", "FastAPI", "Comunicación", "Liderazgo", "Análisis de Datos"]
#     for skill in common_skills:
#         if skill.lower() in raw_text.lower():
#             skills.append(skill)
    
#     # Simulación de experiencia (requiere parsing complejo de texto y fechas)
#     # Buscar patrones como "Cargo en Empresa (Año Inicio - Año Fin)"
#     if "desarrollador" in raw_text.lower():
#         experience.append({"title": "Desarrollador (Simulado)", "company": "Empresa Ficticia", "years": 3})
#     if "analista" in raw_text.lower():
#         experience.append({"title": "Analista de Datos (Simulado)", "company": "DataCorp", "years": 2})

#     # Simulación de educación (requiere parsing de texto y fechas)
#     if "ingeniería informática" in raw_text.lower():
#         education.append({"degree": "Ingeniería Informática (Simulado)", "institution": "Universidad Ficticia", "year": 2020})
    
#     # Intento de extraer correo electrónico y teléfono con regex (más confiable que NER para esto)
#     import re
#     email = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', raw_text)
#     phone = re.search(r'(\+?\d{1,3}[-. ]?)?(\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4})', raw_text) # Simple, puede necesitar ajustes

#     return {
#         "name": name if name else "Candidato", # Proporcionar un valor por defecto
#         "email": email.group(0) if email else None,
#         "phone": phone.group(0) if phone else None,
#         "skills": list(set(skills)), # Eliminar duplicados
#         "experience": experience,
#         "education": education,
#         "raw_text": raw_text
#     }
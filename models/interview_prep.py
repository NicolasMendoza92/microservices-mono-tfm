# models/interview_prep.py

from typing import List
import random
from schemas.cv import ExperienceItem


async def generate_interview_questions(
    candidate_name: str,
    skills: List[str],
    experience: List[ExperienceItem],
    areas_for_development: List[str],
    job_recommendations: List[str],
    num_questions: int = 5
) -> List[str]:

    prompt_parts = [
        f"Genera {num_questions} preguntas de entrevista para el candidato {candidate_name}.",
        f"Sus habilidades clave son: {', '.join(skills)}.",
        f"Tiene experiencia en: {', '.join([exp.title for exp in experience]) if experience else 'ninguna reportada'}.",
        f"Las áreas de desarrollo sugeridas son: {', '.join(areas_for_development) if areas_for_development else 'ninguna'}.",
        f"Los roles recomendados incluyen: {', '.join(job_recommendations)}."
    ]
    prompt = " ".join(prompt_parts) + "\n\nLas preguntas deben ser relevantes para su perfil y los puestos sugeridos, y considerar sus posibles desafíos."
    print(prompt)
    # Simulación de preguntas
    sample_questions = [
        f"Háblame de un momento en que usaste tu habilidad de {random.choice(skills)}.",
        f"¿Cómo manejas los desafíos en el trabajo, especialmente considerando un área como '{random.choice(areas_for_development) if areas_for_development else 'manejo del estrés'}'?",
        f"¿Qué te atrae del rol de {random.choice(job_recommendations)} y cómo crees que tus habilidades se aplicarían?",
        "¿Cuáles son tus objetivos profesionales a corto y largo plazo?",
        "Háblanos de tu experiencia previa que creas que es más relevante para un nuevo rol.",
        "¿Cómo manejas las situaciones de estrés o presión?",
        "¿Qué planes tienes para seguir aprendiendo y desarrollándote profesionalmente?",
    ]
    random.shuffle(sample_questions)
    return sample_questions[:num_questions]
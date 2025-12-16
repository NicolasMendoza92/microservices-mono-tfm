from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
from typing import Optional

# Configuración global del modelo (se carga una sola vez)
_model_name = "PlanTL-GOB-ES/bsc-bart-large-es"
_tokenizer = None
_model = None
_summarizer = None
_device = None

def initialize_summarizer():
    """Inicializa el modelo la primera vez que se llama"""
    global _tokenizer, _model, _summarizer, _device
    
    if _summarizer is None:
        print(f"Cargando modelo: {_model_name}")
        _tokenizer = AutoTokenizer.from_pretrained(_model_name)
        _model = AutoModelForSeq2SeqLM.from_pretrained(_model_name)
        _device = 0 if torch.cuda.is_available() else -1
        _summarizer = pipeline(
            "summarization", 
            model=_model, 
            tokenizer=_tokenizer, 
            device=_device
        )
        print(f"Modelo cargado en device: {_device}")
    
    return _summarizer

def summarize_cv(raw_text: str, max_length: int = 120, chunk_size: int = 1000) -> str:
    # Inicializa si no está cargado
    summarizer = initialize_summarizer()
    # Divide en chunks para textos largos de CV
    chunks = [raw_text[i:i+chunk_size] for i in range(0, len(raw_text), chunk_size)]
    summaries = []
    
    for i, chunk in enumerate(chunks):
        print(f"Procesando chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
        
        # Prompt optimizado para CVs
        prompt = (
            "Resume de forma profesional este CV. "
            "Mantén nombres, fechas y empleadores sin modificar. "
            "No inventes información. "
            f"Texto: {chunk}"
        )
        
        try:
            result = summarizer(
                prompt, 
                max_length=max_length, 
                min_length=40, 
                do_sample=False,
                num_beams=4,
            )[0]['summary_text']
            summaries.append(result)
        except Exception as e:
            print(f"Error en chunk {i}: {e}")
            summaries.append("Resumen no disponible")
    
    # Concatena y limpia
    full_summary = " ".join(summaries)
    return full_summary.strip()[:1200]  # Límite razonable para API

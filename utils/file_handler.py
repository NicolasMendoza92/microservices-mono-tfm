# utils/file_handler.py

import os
from fastapi import UploadFile

# Directorio donde se guardarán los CVs temporalmente o para persistencia
UPLOAD_DIR = "uploaded_cvs"

os.makedirs(UPLOAD_DIR, exist_ok=True)

async def save_upload_file(upload_file: UploadFile) -> str:
    """ Guarda el archivo subido en el disco y devuelve la ruta. """
    file_location = os.path.join(UPLOAD_DIR, upload_file.filename)
    with open(file_location, "wb+") as file_object:
        file_object.write(await upload_file.read())
    return file_location

def get_file_content(file_path: str) -> bytes:
    """ Lee el contenido de un archivo. """
    with open(file_path, "rb") as file_object:
        return file_object.read()

# Podrías añadir funciones para leer PDF, DOCX, etc., aquí o en el microservicio de PLN
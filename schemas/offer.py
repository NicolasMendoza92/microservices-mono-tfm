from pydantic import BaseModel

class OfferInput(BaseModel):
    id: str
    puesto: str
    categoria: str | None = None
    descripcion: str | None = None
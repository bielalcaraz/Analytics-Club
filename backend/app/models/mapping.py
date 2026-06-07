from pydantic import BaseModel
from typing import Optional, List

class ColumnMapping(BaseModel):
    origen: str
    destino: str
    tipo: str  # string | float | integer | date | boolean
    formato: Optional[str] = None  # solo para fechas, ej: %d/%m/%Y
    limpieza: Optional[str] = None  # quitar_pct | quitar_euro | strip
    confianza: str  # alta | media | baja
    nota: Optional[str] = None

class MappingResult(BaseModel):
    columnas: List[ColumnMapping]
    schema_detectado: str

class UploadResponse(BaseModel):
    file_id: str
    headers: List[str]
    sample_rows: List[dict]
    mapping: MappingResult
    total_rows: int

class ConfirmRequest(BaseModel):
    file_id: str
    mapping: MappingResult

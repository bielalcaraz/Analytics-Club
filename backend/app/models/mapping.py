from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any

class ColumnMapping(BaseModel):
    origen: str
    destino: str
    tipo: str  # string | float | integer | date | boolean
    formato: Optional[str] = None  # solo para fechas, ej: %d/%m/%Y
    limpieza: Optional[str] = None  # quitar_pct | quitar_euro | quitar_unidad | strip
    valores: Optional[Dict[str, Optional[str]]] = None  # normalización de valores categóricos
    extraer_unidad: Optional[bool] = None  # separar valor numérico y unidad en columnas distintas
    confianza: str  # alta | media | baja
    nota: Optional[str] = None

    @field_validator("valores", mode="before")
    @classmethod
    def coerce_valores_to_str(cls, v: Any) -> Any:
        """Convierte valores no-string del dict (bool, int, float) a string.
        Claude a veces retorna {"SI": true, "NO": false} en columnas booleanas."""
        if not isinstance(v, dict):
            return v
        result = {}
        for k, val in v.items():
            if val is None or isinstance(val, str):
                result[str(k)] = val
            elif isinstance(val, bool):
                result[str(k)] = "si" if val else "no"
            else:
                result[str(k)] = str(val)
        return result

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


class PersonGroup(BaseModel):
    column_name: str
    valores: List[str]
    nombre_canonico: str
    confianza: str = "alta"


class ReviewPersonsRequest(BaseModel):
    columnas: List[str]
    filas: List[dict]
    grupos_confirmados: List[PersonGroup]

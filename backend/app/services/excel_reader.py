import re
import pandas as pd
import os
from pathlib import Path

ALLOWED_EXTENSIONS = {".xlsx", ".xls"}
MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
TEMP_DIR = Path("/tmp/dataplant")

_STRUCTURAL_START = re.compile(
    r"^\s*(-{3,}|total|subtotal|parcial|elaborado|nota:|>>>)",
    re.IGNORECASE,
)


def clean_structural_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Elimina filas que no son datos:
    - Más del 70 % de columnas vacías/NaN
    - Primera columna con texto estructural (subtotales, pies de página, separadores)
    """
    if df.empty or len(df.columns) == 0:
        return df

    empty_ratio = df.isnull().sum(axis=1) / len(df.columns)
    not_mostly_empty = empty_ratio <= 0.70

    first_col = df.iloc[:, 0].astype(str).str.strip()
    not_structural = ~first_col.str.match(_STRUCTURAL_START, na=False)

    return df[not_mostly_empty & not_structural].reset_index(drop=True)


def init_temp_dir():
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def validate_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def read_excel_safe(file_path: Path) -> pd.DataFrame:
    """Lee el Excel de forma segura y elimina filas estructurales."""
    df = pd.read_excel(file_path, engine="openpyxl", nrows=10000)
    return clean_structural_rows(df)


def extract_sample(df: pd.DataFrame) -> dict:
    """Extrae cabeceras y muestra de filas para enviar a Claude."""
    # Limpiar nombres de columnas para serialización
    sample = df.head(10).copy()
    
    # Convertir tipos no serializables a valores JSON-safe
    for col in sample.columns:
        if sample[col].dtype == "object":
            sample[col] = sample[col].astype(str).replace("nan", None)
        elif pd.api.types.is_datetime64_any_dtype(sample[col]):
            # Serializar como "YYYY-MM-DD" — evita "2025-01-04 00:00:00" por default=str
            sample[col] = sample[col].dt.strftime("%Y-%m-%d").where(sample[col].notna(), None)
        else:
            sample[col] = sample[col].where(sample[col].notna(), None)

    return {
        "headers": df.columns.tolist(),
        "sample_rows": sample.to_dict(orient="records"),
        "total_rows": len(df),
    }


def save_temp_file(file_bytes: bytes, file_id: str, filename: str) -> Path:
    """Guarda el archivo temporalmente para procesarlo después."""
    init_temp_dir()
    ext = Path(filename).suffix.lower()
    path = TEMP_DIR / f"{file_id}{ext}"
    path.write_bytes(file_bytes)
    return path


def get_temp_file(file_id: str) -> Path | None:
    """Recupera un archivo temporal por su ID."""
    for ext in ALLOWED_EXTENSIONS:
        path = TEMP_DIR / f"{file_id}{ext}"
        if path.exists():
            return path
    return None


def cleanup_temp_file(file_id: str):
    """Elimina el archivo temporal tras procesarlo."""
    for ext in ALLOWED_EXTENSIONS:
        path = TEMP_DIR / f"{file_id}{ext}"
        if path.exists():
            os.remove(path)

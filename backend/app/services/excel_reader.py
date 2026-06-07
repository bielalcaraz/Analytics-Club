import pandas as pd
import os
from pathlib import Path

ALLOWED_EXTENSIONS = {".xlsx", ".xls"}
MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
TEMP_DIR = Path("/tmp/dataplant")


def init_temp_dir():
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def validate_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def read_excel_safe(file_path: Path) -> pd.DataFrame:
    """Lee el Excel de forma segura sin ejecutar macros."""
    return pd.read_excel(
        file_path,
        engine="openpyxl",
        nrows=10000,  # límite preventivo
    )


def extract_sample(df: pd.DataFrame) -> dict:
    """Extrae cabeceras y muestra de filas para enviar a Claude."""
    # Limpiar nombres de columnas para serialización
    sample = df.head(10).copy()
    
    # Convertir tipos no serializables a string
    for col in sample.columns:
        if sample[col].dtype == "object":
            sample[col] = sample[col].astype(str).replace("nan", None)
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

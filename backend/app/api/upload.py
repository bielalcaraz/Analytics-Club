import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.mapping import UploadResponse, ConfirmRequest
from app.services.excel_reader import (
    validate_extension,
    read_excel_safe,
    extract_sample,
    save_temp_file,
    get_temp_file,
    cleanup_temp_file,
    MAX_SIZE_BYTES,
)
from app.services.claude_mapper import map_columns_with_claude
from app.services.transformer import apply_mapping, dataframe_to_json

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_excel(file: UploadFile = File(...)):
    """
    Paso 1: Recibe el Excel, extrae muestra y llama a Claude para mapear columnas.
    """
    # Validar extensión
    if not validate_extension(file.filename or ""):
        raise HTTPException(
            status_code=400,
            detail="Formato no válido. Solo se aceptan archivos .xlsx y .xls"
        )

    # Leer bytes y validar tamaño
    file_bytes = await file.read()
    if len(file_bytes) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo supera el límite de 20 MB"
        )

    # Generar ID único para esta sesión de procesamiento
    file_id = str(uuid.uuid4())

    # Guardar temporalmente
    temp_path = save_temp_file(file_bytes, file_id, file.filename or "archivo.xlsx")

    try:
        # Leer con pandas de forma segura
        df = read_excel_safe(temp_path)

        if df.empty:
            raise HTTPException(status_code=400, detail="El archivo está vacío o no tiene datos legibles")

        # Extraer muestra para Claude
        sample_data = extract_sample(df)

        # Llamar a Claude para mapear columnas
        mapping = map_columns_with_claude(
            headers=sample_data["headers"],
            sample_rows=sample_data["sample_rows"],
        )

        return UploadResponse(
            file_id=file_id,
            headers=sample_data["headers"],
            sample_rows=sample_data["sample_rows"],
            mapping=mapping,
            total_rows=sample_data["total_rows"],
        )

    except HTTPException:
        cleanup_temp_file(file_id)
        raise
    except Exception as e:
        cleanup_temp_file(file_id)
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {str(e)}")


@router.post("/confirm")
async def confirm_mapping(body: ConfirmRequest):
    """
    Paso 2: Recibe el mapeo confirmado por el usuario y transforma el Excel completo.
    """
    # Recuperar el archivo temporal
    temp_path = get_temp_file(body.file_id)
    if not temp_path:
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado. Por favor vuelve a subir el Excel."
        )

    try:
        # Leer el Excel completo
        df = read_excel_safe(temp_path)

        # Aplicar transformaciones con pandas (código determinista, sin IA)
        df_normalizado = apply_mapping(df, body.mapping)

        # Convertir a JSON serializable
        rows = dataframe_to_json(df_normalizado)

        return {
            "columnas": df_normalizado.columns.tolist(),
            "filas": rows,
            "total_filas": len(rows),
            "schema": body.mapping.schema_detectado,
        }

    finally:
        # Limpiar archivo temporal siempre
        cleanup_temp_file(body.file_id)


@router.get("/health")
async def health():
    return {"status": "ok"}

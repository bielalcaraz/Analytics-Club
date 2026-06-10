import uuid
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.mapping import UploadResponse, ConfirmRequest, ReviewPersonsRequest
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
from app.services.transformer import apply_mapping_with_warnings, dataframe_to_json, _PERSON_COLS
from app.services.text_normalizer import detect_person_groups
from app.services.schema_validator import validate_and_standardize, SchemaValidationError

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_excel(file: UploadFile = File(...)):
    """
    Paso 1: Recibe el Excel, extrae muestra y llama a Claude para mapear columnas.
    """
    if not validate_extension(file.filename or ""):
        raise HTTPException(
            status_code=400,
            detail="Formato no válido. Solo se aceptan archivos .xlsx y .xls"
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="El archivo supera el límite de 20 MB"
        )

    file_id = str(uuid.uuid4())
    temp_path = save_temp_file(file_bytes, file_id, file.filename or "archivo.xlsx")

    try:
        df = read_excel_safe(temp_path)
        if df.empty:
            raise HTTPException(status_code=400, detail="El archivo está vacío o no tiene datos legibles")

        sample_data = extract_sample(df)
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
    Paso 2: Recibe el mapeo confirmado, transforma el Excel y detecta grupos de personas.
    Si grupos_personas no está vacío, el frontend mostrará el paso de revisión de personas.
    """
    temp_path = get_temp_file(body.file_id)
    if not temp_path:
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado. Por favor vuelve a subir el Excel."
        )

    try:
        df = read_excel_safe(temp_path)

        df_normalizado, advertencias, normalizaciones, posibles_duplicados = (
            apply_mapping_with_warnings(df, body.mapping)
        )

        # Validación final de esquema canónico: garantiza columnas estándar
        # para que los dashboards funcionen igual independientemente de la empresa
        try:
            df_normalizado, schema_warnings = validate_and_standardize(
                df_normalizado, body.mapping.schema_detectado
            )
        except SchemaValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        advertencias.extend(schema_warnings)

        # Detectar grupos de nombres de personas para revisión manual
        grupos_personas = []
        for col in body.mapping.columnas:
            if col.tipo != "string":
                continue
            dest = col.destino
            if dest not in df_normalizado.columns:
                continue
            if not any(kw in dest.lower() for kw in _PERSON_COLS):
                continue
            unique_vals = [
                str(v) for v in df_normalizado[dest].dropna().unique()
                if str(v) not in ("", "nan", "None")
            ]
            if len(unique_vals) < 2:
                continue
            grupos = detect_person_groups(dest, unique_vals)
            grupos_personas.extend(grupos)

        rows = dataframe_to_json(df_normalizado)

        return {
            "columnas": df_normalizado.columns.tolist(),
            "filas": rows,
            "total_filas": len(rows),
            "schema": body.mapping.schema_detectado,
            "advertencias": advertencias,
            "normalizaciones": normalizaciones,
            "posibles_duplicados": posibles_duplicados,
            "grupos_personas": grupos_personas,
        }

    finally:
        cleanup_temp_file(body.file_id)


@router.post("/review-persons")
async def review_persons(body: ReviewPersonsRequest):
    """
    Paso 3 (opcional): Aplica las unificaciones de nombres confirmadas por el usuario.
    Solo modifica los grupos que el usuario ha aprobado explícitamente.
    """
    df = pd.DataFrame(body.filas)
    # Preservar orden de columnas
    cols = [c for c in body.columnas if c in df.columns]
    df = df[cols]

    for grupo in body.grupos_confirmados:
        if grupo.column_name not in df.columns:
            continue
        repl = {
            v: grupo.nombre_canonico
            for v in grupo.valores
            if v != grupo.nombre_canonico
        }
        if repl:
            df[grupo.column_name] = df[grupo.column_name].replace(repl)

    rows = dataframe_to_json(df)
    return {
        "columnas": df.columns.tolist(),
        "filas": rows,
        "total_filas": len(rows),
    }


@router.get("/health")
async def health():
    return {"status": "ok"}

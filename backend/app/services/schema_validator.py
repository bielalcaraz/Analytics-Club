import pandas as pd

from app.schemas.canonical import CANONICAL_SCHEMAS


class SchemaValidationError(Exception):
    pass


def validate_and_standardize(df: pd.DataFrame, schema_name: str) -> tuple[pd.DataFrame, list[str]]:
    """
    Último paso del pipeline: garantiza que el DataFrame cumple el esquema
    canónico del schema detectado, para que los dashboards funcionen igual
    independientemente de la empresa de origen.

    1. Verifica que las columnas requeridas existen (si falta alguna, lanza
       SchemaValidationError).
    2. Añade las columnas opcionales que falten como null.
    3. Verifica que las columnas con enum solo tengan valores válidos —
       las filas fuera de rango se reportan como advertencia, no se eliminan.
    4. Reordena columnas: requeridas, luego opcionales, luego extra.

    Devuelve (df_validado, advertencias). Si schema_name no tiene esquema
    canónico definido (ej. "otro"), devuelve el df sin cambios.
    """
    schema = CANONICAL_SCHEMAS.get(schema_name)
    if schema is None:
        return df, []

    result = df.copy()
    advertencias: list[str] = []

    required = schema.get("required", {})
    optional = schema.get("optional", {})
    enums = schema.get("enums", {})

    # 1. Columnas requeridas
    for col in required:
        if col not in result.columns:
            raise SchemaValidationError(
                f"Columna requerida '{col}' no encontrada en los datos normalizados"
            )

    # 1b. Columnas requeridas con muchos valores nulos
    total_filas = len(result)
    if total_filas > 0:
        for col in required:
            n_nulos = int(result[col].isna().sum())
            if n_nulos / total_filas > 0.2:
                advertencias.append(
                    f"Columna requerida '{col}' tiene {n_nulos} filas sin valor — "
                    f"revisa los datos de origen."
                )

    # 2. Columnas opcionales faltantes -> null
    for col in optional:
        if col not in result.columns:
            result[col] = None

    # 3. Validación de enums
    for col, valores_validos in enums.items():
        if col not in result.columns:
            continue
        invalid_mask = result[col].notna() & ~result[col].isin(valores_validos)
        if invalid_mask.any():
            valores_invalidos = sorted(str(v) for v in result.loc[invalid_mask, col].unique())
            advertencias.append(
                f"Columna '{col}': {int(invalid_mask.sum())} fila(s) con valores fuera "
                f"del enum esperado {valores_validos}: {valores_invalidos}"
            )

    # 4. Reordenar columnas: requeridas, opcionales, extra
    required_cols = list(required.keys())
    optional_cols = list(optional.keys())
    known_cols = set(required_cols) | set(optional_cols)
    extra_cols = [c for c in result.columns if c not in known_cols]
    result = result[required_cols + optional_cols + extra_cols]

    return result, advertencias

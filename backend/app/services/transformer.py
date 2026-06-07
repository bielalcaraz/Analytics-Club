import pandas as pd
from app.models.mapping import MappingResult, ColumnMapping


def apply_mapping(df: pd.DataFrame, mapping: MappingResult) -> pd.DataFrame:
    """
    Aplica el mapeo confirmado al DataFrame completo.
    Código determinista — no hay IA aquí, solo pandas.
    """
    result = df.copy()

    for col in mapping.columnas:
        if col.origen not in result.columns:
            continue

        # 1. Aplicar limpieza previa si es necesaria
        if col.limpieza:
            result[col.origen] = _apply_cleaning(result[col.origen], col.limpieza)

        # 2. Convertir al tipo destino
        result[col.origen] = _convert_type(result[col.origen], col)

    # 3. Renombrar columnas según mapeo
    rename_map = {
        c.origen: c.destino
        for c in mapping.columnas
        if c.origen in result.columns
    }
    result = result.rename(columns=rename_map)

    # 4. Mantener solo columnas mapeadas (descartar las no reconocidas)
    destino_cols = [c.destino for c in mapping.columnas if c.origen in df.columns]
    result = result[destino_cols]

    return result


def _apply_cleaning(series: pd.Series, limpieza: str) -> pd.Series:
    """Limpieza de texto antes de la conversión de tipo."""
    s = series.astype(str)

    if limpieza == "quitar_pct":
        s = s.str.replace("%", "", regex=False).str.replace(",", ".", regex=False).str.strip()
    elif limpieza == "quitar_euro":
        s = s.str.replace("€", "", regex=False).str.replace(",", ".", regex=False).str.strip()
    elif limpieza == "strip":
        s = s.str.strip()

    return s


def _convert_type(series: pd.Series, col: ColumnMapping) -> pd.Series:
    """Convierte la serie al tipo de dato correcto."""
    try:
        if col.tipo == "float":
            return pd.to_numeric(series, errors="coerce")
        elif col.tipo == "integer":
            return pd.to_numeric(series, errors="coerce").astype("Int64")
        elif col.tipo == "date" and col.formato:
            return pd.to_datetime(series, format=col.formato, errors="coerce")
        elif col.tipo == "boolean":
            return series.map(
                lambda x: True if str(x).lower() in ("1", "si", "sí", "yes", "true", "s")
                else False if str(x).lower() in ("0", "no", "false", "n")
                else None
            )
        else:
            return series.astype(str).replace("nan", None)
    except Exception:
        return series


def dataframe_to_json(df: pd.DataFrame) -> list[dict]:
    """Convierte el DataFrame normalizado a JSON serializable."""
    result = df.copy()

    for col in result.columns:
        if result[col].dtype == "datetime64[ns]":
            result[col] = result[col].dt.strftime("%Y-%m-%d").where(result[col].notna(), None)
        elif hasattr(result[col], "dtype") and str(result[col].dtype) == "Int64":
            result[col] = result[col].astype(object).where(result[col].notna(), None)

    return result.where(result.notna(), None).to_dict(orient="records")

import re
import json
import anthropic
import pandas as pd
from app.models.mapping import MappingResult, ColumnMapping
from app.services.text_normalizer import normalize_free_text

_DATE_FORMATS = [
    "%d/%m/%y", "%d/%m/%Y",
    "%d-%m-%y", "%d-%m-%Y",
    "%m/%d/%y", "%m/%d/%Y",
    "%Y-%m-%d",
    "%B %d %Y", "%B %d, %Y",   # "January 4 2025", "January 4, 2025"
    "%d %B %Y", "%d %B, %Y",   # "4 January 2025"
]

# Regex to split a cell like "3,45€/kg" or "850 u" into number + unit
_EXTRACT_RE = re.compile(r"^\s*(?P<num>-?\d[\d.,]*)\s*(?P<unit>\S+)?\s*$")

_UNIT_ALIASES: dict[str, str] = {
    "u": "uds", "U": "uds", "ud": "uds", "Ud": "uds",
}

# Fallback para estado_stock: se aplica DESPUÉS del dict valores de Claude,
# para cubrir valores que no aparecieron en la muestra de 10 filas.
_ESTADO_STOCK_FALLBACK: dict[str, str] = {
    "ok": "ok", "correcto": "ok", "normal": "ok", "bien": "ok", "disponible": "ok",
    "bajo": "bajo", "bajo stock": "bajo", "poco stock": "bajo", "insuficiente": "bajo",
    "critico": "critico", "crítico": "critico", "rojo": "critico",
    "exceso": "exceso", "exceso stock": "exceso", "sobrestock": "exceso",
    "exceso de stock": "exceso", "sobreabastecimiento": "exceso",
    "bloqueado": "bloqueado", "retenido": "bloqueado", "inmovilizado": "bloqueado",
    "cuarentena": "en_cuarentena", "en cuarentena": "en_cuarentena",
    "qc hold": "en_cuarentena", "hold": "en_cuarentena",
}


def extract_value_and_unit(val) -> dict:
    """
    '3,45€/kg' → {'valor': 3.45, 'unidad': '€/kg'}
    '850 u'    → {'valor': 850.0, 'unidad': 'uds'}
    '0.85'     → {'valor': 0.85, 'unidad': None}
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return {"valor": None, "unidad": None}
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", ""):
        return {"valor": None, "unidad": None}

    m = _EXTRACT_RE.match(s)
    if not m:
        return {"valor": None, "unidad": None}

    num_str = m.group("num")
    raw_unit = (m.group("unit") or "").strip()

    # Parse number: handle European format "1.200,00" and plain "3,45"
    ns = num_str
    if "." in ns and "," in ns:
        ns = ns.replace(".", "").replace(",", ".")
    else:
        ns = ns.replace(",", ".")
    try:
        valor = float(ns)
    except ValueError:
        valor = None

    if not raw_unit:
        return {"valor": valor, "unidad": None}

    # Normalize compound units (€/u → €/uds) and standalone aliases
    unit = re.sub(r"/[uU]\b", "/uds", raw_unit)
    unit = _UNIT_ALIASES.get(unit, unit)
    return {"valor": valor, "unidad": unit or None}


def apply_mapping(df: pd.DataFrame, mapping: MappingResult) -> pd.DataFrame:
    result = df.copy()

    for col in mapping.columnas:
        if col.origen not in result.columns:
            continue

        if getattr(col, "extraer_unidad", None):
            extracted = result[col.origen].apply(extract_value_and_unit)
            result[col.origen] = pd.to_numeric(
                extracted.apply(lambda d: d["valor"]), errors="coerce"
            )
            result[col.origen + "_unidad"] = extracted.apply(lambda d: d["unidad"])
            continue

        if col.limpieza:
            result[col.origen] = _apply_cleaning(result[col.origen], col.limpieza)

        result[col.origen] = _convert_type(result[col.origen], col)

        if col.valores and col.tipo != "boolean":
            # Para estado_stock, enriquecer el dict de Claude con el fallback canónico.
            # Así los valores fuera de la muestra (ej: "exceso stock" en fila 23)
            # quedan cubiertos aunque Claude no los haya visto.
            mapping_dict = col.valores
            if col.destino == "estado_stock":
                # fallback tiene menor prioridad: Claude manda si tiene la clave
                merged = {k: v for k, v in _ESTADO_STOCK_FALLBACK.items()}
                merged.update({k: v for k, v in col.valores.items() if v is not None})
                mapping_dict = merged
            def _map_stock(v, m=mapping_dict):
                if not isinstance(v, str) or v in ("None", "nan", ""):
                    return None
                return m.get(v.lower(), m.get(v, None))
            result[col.origen] = result[col.origen].astype(str).str.strip().map(_map_stock)
        elif col.destino == "estado_stock":
            # Claude no generó valores dict para esta columna — aplicar fallback igualmente
            def _map_stock_fallback(v):
                if not isinstance(v, str) or v in ("None", "nan", ""):
                    return None
                return _ESTADO_STOCK_FALLBACK.get(v.lower().strip(), None)
            result[col.origen] = result[col.origen].astype(str).str.strip().map(_map_stock_fallback)

    rename_map = {}
    for c in mapping.columnas:
        if c.origen in result.columns:
            rename_map[c.origen] = c.destino
        if getattr(c, "extraer_unidad", None) and (c.origen + "_unidad") in result.columns:
            rename_map[c.origen + "_unidad"] = c.destino + "_unidad"
    result = result.rename(columns=rename_map)

    destino_cols = []
    for c in mapping.columnas:
        if c.origen in df.columns:
            destino_cols.append(c.destino)
            if getattr(c, "extraer_unidad", None):
                destino_cols.append(c.destino + "_unidad")
    result = result[[col for col in destino_cols if col in result.columns]]

    result = _drop_garbage_rows(result)

    return result


def apply_mapping_with_warnings(
    df: pd.DataFrame, mapping: MappingResult
) -> tuple[pd.DataFrame, list[str], dict, dict]:
    """
    Pipeline completo:
    1. apply_mapping  — rename, tipos, limpieza, valores dict
    2. _normalize_text_columns  — segunda llamada a Claude para texto libre
    3. Detección de duplicados exactos
    4. Detección de referencias similares (Levenshtein)
    Devuelve (df, advertencias, normalizaciones, posibles_duplicados).
    """
    result = apply_mapping(df, mapping)

    # Segunda llamada a Claude: normalizar texto libre
    result, normalizaciones = _normalize_text_columns(result, mapping)

    # Detectar duplicados exactos
    warnings: list[str] = []
    n_before = len(result)
    result = result.drop_duplicates(keep="first").reset_index(drop=True)
    n_removed = n_before - len(result)
    if n_removed > 0:
        warnings.append(
            f"Se encontraron {n_removed} fila(s) duplicada(s) y fueron eliminadas"
        )

    # Detectar referencias similares (posibles alias del mismo artículo)
    posibles_duplicados = _detect_similar_refs(result, mapping)

    return result, warnings, normalizaciones, posibles_duplicados


_SYSTEM_PROMPT_DUPDETECT = """\
Eres un experto en referencias de artículos industriales del sector metal. \
Tu tarea es identificar referencias que sean genuinamente el mismo artículo \
escrito de formas distintas.

REGLAS CRÍTICAS:
- Referencias de la misma familia pero distinto tamaño/diámetro/medida NO son \
duplicados: VLV-DN25, VLV-DN50, VLV-DN80 son válvulas distintas. \
BRD-1", BRD-3/4" son bridas distintas. COD-45-INX, COD-90-INX son codos distintos.
- SÍ son duplicados: PN-4521-A y 4521-A y PN4521A (mismo código con/sin prefijo). \
CIL-8800 y 8800-CIL (mismo código invertido). \
REF-001 y ref-001 (mismo código distinta capitalización).
- Si tienes dudas, NO lo marques como duplicado. Solo marca los casos donde \
estás seguro al 90%+ de que es el mismo artículo.

Devuelve ÚNICAMENTE un JSON válido:
{"grupos_duplicados": [["valor_a", "valor_b"], ["valor_c", "valor_d", "valor_e"]]}
Si no hay duplicados reales devuelve: {"grupos_duplicados": []}
Sin texto adicional, solo JSON.\
"""


def _detect_duplicates_with_claude(
    column_name: str, unique_values: list[str]
) -> list[list[str]]:
    """
    Llama a Claude para identificar referencias que son el mismo artículo
    escrito de formas distintas. Devuelve lista de grupos, o [] si no hay.
    """
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=_SYSTEM_PROMPT_DUPDETECT,
            messages=[{
                "role": "user",
                "content": (
                    f"Columna: {column_name}\n"
                    f"Valores únicos: {json.dumps(unique_values, ensure_ascii=False)}"
                ),
            }],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        groups = data.get("grupos_duplicados", [])
        # Filtrar grupos con menos de 2 elementos (respuesta mal formada)
        return [g for g in groups if isinstance(g, list) and len(g) >= 2]
    except Exception:
        return []


def _detect_similar_refs(df: pd.DataFrame, mapping: MappingResult) -> dict:
    """
    Para columnas de referencia / part_number, llama a Claude para detectar
    referencias que son el mismo artículo escrito de formas distintas.
    Ignora columnas con más de 50 valores únicos (IDs secuenciales).
    Devuelve {col_name: [[grupo1_val1, val2, ...], [grupo2_val1, ...]]}
    """
    REF_COLS = re.compile(r"referencia|part_number|part_no|codigo_articulo", re.IGNORECASE)
    result: dict = {}

    for col in mapping.columnas:
        if col.tipo != "string":
            continue
        if not REF_COLS.search(col.destino):
            continue
        if col.destino not in df.columns:
            continue

        vals = [
            str(v) for v in df[col.destino].dropna().unique()
            if str(v) not in ("", "nan", "None")
        ]
        if len(vals) < 2 or len(vals) > 50:
            continue

        groups = _detect_duplicates_with_claude(col.destino, vals)
        if groups:
            result[col.destino] = groups

    return result


# Columnas de identificadores/códigos — nunca pasan por normalize_free_text
_SKIP_NORM = (
    "referencia", "id", "codigo", "orden", "maquina",
    "descripcion", "observacion", "nota", "comentario", "detalle",
)

# Columnas de personas — solo strip + title case, nunca Claude
_PERSON_COLS = (
    "inspector", "tecnico", "operario", "responsable",
    "nombre_inspector", "nombre_operario", "nombre_tecnico", "tecnico_responsable",
)


def _safe_map(orig, norm) -> str:
    """Descarta la normalización si el valor es más de 3 chars más largo que el original."""
    if pd.isna(orig) or pd.isna(norm):
        return orig
    if len(str(norm)) > len(str(orig)) + 3:
        return orig
    return norm


def _normalize_text_columns(
    df: pd.DataFrame, mapping: MappingResult
) -> tuple[pd.DataFrame, dict]:
    """
    Para cada columna de tipo string con 2-30 valores únicos (sin contar nulos),
    llama a Claude para normalizar variaciones semánticas.
    Columnas en _SKIP_NORM: ignoradas.
    Columnas en _PERSON_COLS: solo strip + title case, nunca Claude.
    Para el resto: Claude + validación de longitud (_safe_map).
    Devuelve el df modificado y el dict de cambios aplicados.
    """
    normalizaciones: dict = {}

    for col in mapping.columnas:
        if col.tipo != "string":
            continue
        if col.destino not in df.columns:
            continue
        if col.valores:
            continue

        dest = col.destino.lower()

        if any(kw in dest for kw in _SKIP_NORM):
            continue

        # Columnas de persona: solo strip + title case, nunca Claude
        if any(kw in dest for kw in _PERSON_COLS):
            before = df[col.destino].copy()
            df[col.destino] = (
                df[col.destino]
                .astype(str)
                .str.strip()
                .str.title()
                .where(df[col.destino].notna(), df[col.destino])
            )
            changes = {
                str(o): str(n)
                for o, n in zip(before, df[col.destino])
                if pd.notna(o) and str(o) != str(n)
            }
            if changes:
                normalizaciones[col.destino] = changes
            continue

        unique_vals = [
            str(v) for v in df[col.destino].dropna().unique()
            if str(v) not in ("", "nan", "None")
        ]
        if not (2 <= len(unique_vals) <= 30):
            continue

        norm_dict = normalize_free_text(col.destino, unique_vals)
        if not norm_dict:
            continue

        # Aplicar con seguro de longitud: si normalizado > original + 3 chars, descartar
        df[col.destino] = df[col.destino].apply(
            lambda x, d=norm_dict: _safe_map(x, d.get(str(x), x)) if pd.notna(x) else x
        )

        changes = {k: v for k, v in norm_dict.items() if k != v}
        if changes:
            normalizaciones[col.destino] = changes

    return df, normalizaciones


# ── Limpieza ──────────────────────────────────────────────────────────────────

def _apply_cleaning(series: pd.Series, limpieza: str) -> pd.Series:
    s = series.astype(str)

    if limpieza == "quitar_pct":
        # Normaliza a fracción decimal (0-1):
        #   "2,3%"  → 0.023  (quitar %, dividir entre 100)
        #   "0.034" → 0.034  (ya es fracción, dejar igual)
        #   "2"     → 0.02   (asumir porcentaje, dividir entre 100)
        return s.apply(_normalize_pct)

    elif limpieza == "quitar_euro":
        # Remove trailing € (and any unit suffix after it, e.g. "€/kg")
        s = s.str.replace(r"[€$][^\d]*$", "", regex=True)
        # Remove leading currency prefix (e.g. "EUR 315" → "315")
        s = s.str.replace(r"^[^\d]*", "", regex=True)
        return s.str.replace(",", ".", regex=False).str.strip()

    elif limpieza in ("quitar_unidad", "quitar_unidades"):
        # "850 u" → "850", "415 kg" → "415", "1.200 pcs" → "1200"
        extracted = s.str.extract(r"^([\d\s\.,\-]+)", expand=False).str.strip()
        return extracted.str.replace(",", ".", regex=False)

    elif limpieza == "strip":
        return s.str.strip()

    return s


def _normalize_pct(val) -> str | None:
    """Convierte cualquier representación de porcentaje a fracción decimal."""
    s = str(val).strip() if val is not None else ""
    if not s or s.lower() in ("nan", "none", ""):
        return None
    has_pct = "%" in s
    s = s.replace("%", "").replace(",", ".").strip()
    try:
        num = float(s)
        if has_pct:
            return str(num / 100)
        elif 0.0 <= num <= 1.0:
            return str(num)
        else:
            return str(num / 100)
    except (ValueError, OverflowError):
        return str(val)


# ── Conversión de tipos ───────────────────────────────────────────────────────

def _convert_type(series: pd.Series, col: ColumnMapping) -> pd.Series:
    try:
        if col.tipo == "float":
            return pd.to_numeric(_fix_numeric(series), errors="coerce")
        elif col.tipo == "integer":
            return pd.to_numeric(_fix_numeric(series), errors="coerce").astype("Int64")
        elif col.tipo == "date":
            return _parse_dates_robust(series, hint_format=col.formato)

        elif col.tipo == "boolean":
            _TRUE  = {"1", "si", "sí", "yes", "true", "s", "t", "verdadero", "v"}
            _FALSE = {"0", "no", "false", "n", "f", "falso"}
            def _bool_str(x):
                v = str(x).lower().strip()
                if v in _TRUE:
                    return "si"
                if v in _FALSE:
                    return "no"
                return None
            return series.map(_bool_str)
        else:
            return series.astype(str).replace("nan", None)
    except Exception:
        return series


def _fix_numeric(series: pd.Series) -> pd.Series:
    """
    Normaliza separadores numéricos europeos antes de pd.to_numeric.
    - "1.200"  → "1200"  (miles con punto, solo si primer dígito es 1-9)
    - "1,5"   → "1.5"
    - "0.034" → "0.034"  (NO se toca — es un decimal, no miles)
    """
    # Patrón de miles: empieza con 1-9, luego grupos de .DDD
    THOUSANDS_RE = re.compile(r"^[1-9]\d{0,2}(\.\d{3})+$")

    def fix(val):
        if pd.isna(val):
            return val
        s = str(val).strip()
        if not s or s.lower() == "nan":
            return None
        if THOUSANDS_RE.match(s):
            return s.replace(".", "")   # "1.200" → "1200"
        return s.replace(",", ".")      # decimal con coma → punto

    return series.apply(fix)


def _parse_dates_robust(series: pd.Series, hint_format: str | None = None) -> pd.Series:
    # openpyxl may already have parsed dates as datetime64 — return directly
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    s = series.astype(str).str.strip()

    # Excel serial numbers: pd.to_numeric detects both "45780" and "45780.0"
    # Range 20000–60000 ≈ years 1954–2064
    numeric_s = pd.to_numeric(s, errors="coerce")
    serial_mask = result.isna() & numeric_s.notna() & (numeric_s >= 20000) & (numeric_s <= 60000)
    if serial_mask.any():
        excel_epoch = pd.Timestamp("1899-12-30")
        def serial_to_date(v):
            try:
                return excel_epoch + pd.Timedelta(days=int(float(v)))
            except Exception:
                return pd.NaT
        result[serial_mask] = s[serial_mask].apply(serial_to_date).values

    # hint_format es válido solo si es un único código strptime (no una descripción como
    # "mixto: %d/%m/%y, %d-%m-%Y, ..." que Claude a veces devuelve)
    _valid_hint = (
        hint_format is not None
        and "%" in hint_format
        and len(hint_format) <= 30
        and "," not in hint_format
    )
    formats = (
        ([hint_format] if _valid_hint else [])
        + _DATE_FORMATS
        + ["%Y-%m-%d %H:%M:%S"]
    )

    for fmt in formats:
        pending = result.isna() & s.notna() & (s != "") & (s != "nan") & (s != "NaT")
        if not pending.any():
            break
        parsed = pd.to_datetime(s[pending], format=fmt, errors="coerce")
        filled = parsed.notna()
        if filled.any():
            result[pending & filled.reindex(result.index, fill_value=False)] = parsed[filled].values

    # Final fallback: pandas auto-parser for any remaining unparsed values
    # (handles unusual formats like "January 4 2025" not covered above)
    pending = result.isna() & s.notna() & (s != "") & (s != "nan") & (s != "NaT")
    if pending.any():
        parsed = pd.to_datetime(s[pending], errors="coerce", dayfirst=True)
        filled = parsed.notna()
        if filled.any():
            result[pending & filled.reindex(result.index, fill_value=False)] = parsed[filled].values

    return result


def _drop_garbage_rows(df: pd.DataFrame) -> pd.DataFrame:
    all_null = df.isnull().all(axis=1)
    GARBAGE_PATTERNS = r">>|TOTAL|SUBTOTAL|PARCIAL"
    str_cols = df.select_dtypes(include="object").columns
    is_garbage = pd.Series(False, index=df.index)
    for col in str_cols:
        is_garbage |= df[col].astype(str).str.contains(
            GARBAGE_PATTERNS, case=False, na=False, regex=True
        )
    return df[~all_null & ~is_garbage].reset_index(drop=True)


def dataframe_to_json(df: pd.DataFrame) -> list[dict]:
    result = df.copy()
    for col in result.columns:
        if pd.api.types.is_datetime64_any_dtype(result[col]):
            result[col] = result[col].dt.strftime("%Y-%m-%d").where(result[col].notna(), None)
        elif hasattr(result[col], "dtype") and str(result[col].dtype) == "Int64":
            result[col] = result[col].astype(object).where(result[col].notna(), None)
    return result.where(result.notna(), None).to_dict(orient="records")

import json
import logging

import anthropic
import numpy as np
import pandas as pd

from app.prompts import DASHBOARD_PROMPT
from app.models.dashboard import DashboardSpec

logger = logging.getLogger(__name__)

_TOP_VALUES_LIMIT = 5


def _to_native(value):
    """Convierte tipos numpy a tipos nativos serializables en JSON."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def profile_dataframe(df: pd.DataFrame) -> dict:
    """
    Genera un perfil por columna del DataFrame normalizado, sin incluir
    nunca filas completas — solo estadísticas agregadas:
    - dtype, % de nulos, número de valores únicos
    - min/max para columnas numéricas y de fecha
    - top 5 valores más frecuentes para columnas categóricas
    """
    profile: dict = {}
    n_rows = len(df)

    for col in df.columns:
        series = df[col]
        null_pct = round(float(series.isna().mean() * 100), 2) if n_rows else 0.0

        col_profile: dict = {
            "dtype": str(series.dtype),
            "null_pct": null_pct,
            "n_unique": int(series.nunique(dropna=True)),
        }

        non_null = series.dropna()

        if pd.api.types.is_datetime64_any_dtype(series):
            if not non_null.empty:
                col_profile["min"] = non_null.min().strftime("%Y-%m-%d")
                col_profile["max"] = non_null.max().strftime("%Y-%m-%d")
        elif pd.api.types.is_numeric_dtype(series):
            if not non_null.empty:
                col_profile["min"] = _to_native(non_null.min())
                col_profile["max"] = _to_native(non_null.max())
        else:
            top = non_null.astype(str).value_counts().head(_TOP_VALUES_LIMIT)
            if not top.empty:
                col_profile["top_values"] = top.index.tolist()

        profile[col] = col_profile

    return profile


def suggest_dashboard(df: pd.DataFrame) -> DashboardSpec:
    """
    Envía el perfil del DataFrame a Claude y devuelve la propuesta de
    dashboard como DashboardSpec. Solo se envían estadísticas agregadas,
    nunca las filas del dataset.
    """
    client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno

    profile = profile_dataframe(df)

    user_message = (
        "Perfil de las columnas del dataset normalizado:\n"
        f"{json.dumps(profile, ensure_ascii=False, default=str)}\n\n"
        "Devuelve ÚNICAMENTE el JSON del DashboardSpec."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=DASHBOARD_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()

    # Limpiar por si Claude añade backticks accidentalmente
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    data = json.loads(raw)
    return DashboardSpec(**data)


def validate_spec(spec: DashboardSpec, df: pd.DataFrame) -> DashboardSpec:
    """
    Filtra la DashboardSpec descartando gráficos que no se puedan calcular
    sobre el DataFrame real:
    - measure o dimension referencian columnas inexistentes
    - aggregation sum/mean/min/max sobre una columna no numérica
    - granularity definido sobre una dimension que no es de tipo fecha

    Cada gráfico descartado se registra con un warning explicando el motivo.
    """
    valid_charts = []

    for chart in spec.charts:
        if chart.measure not in df.columns:
            logger.warning(
                "Gráfico '%s' descartado: la columna de medida '%s' no existe en los datos",
                chart.id, chart.measure,
            )
            continue

        if chart.dimension is not None and chart.dimension not in df.columns:
            logger.warning(
                "Gráfico '%s' descartado: la columna de dimensión '%s' no existe en los datos",
                chart.id, chart.dimension,
            )
            continue

        if chart.aggregation in ("sum", "mean", "min", "max") and not pd.api.types.is_numeric_dtype(df[chart.measure]):
            logger.warning(
                "Gráfico '%s' descartado: aggregation '%s' no es válida sobre la columna no "
                "numérica '%s' (dtype=%s)",
                chart.id, chart.aggregation, chart.measure, df[chart.measure].dtype,
            )
            continue

        if chart.granularity is not None:
            if chart.dimension is None or not pd.api.types.is_datetime64_any_dtype(df[chart.dimension]):
                logger.warning(
                    "Gráfico '%s' descartado: granularity '%s' requiere una dimensión de tipo "
                    "fecha, pero '%s' no lo es",
                    chart.id, chart.granularity, chart.dimension,
                )
                continue

        valid_charts.append(chart)

    return DashboardSpec(charts=valid_charts)

import logging

import numpy as np
import pandas as pd

from app.models.dashboard import ChartSpec, DashboardSpec

logger = logging.getLogger(__name__)

_GRANULARITY_FREQ = {"day": "D", "week": "W", "month": "M"}


def _to_native(value):
    """Convierte tipos numpy/pandas a tipos nativos serializables en JSON."""
    if value is None:
        return None
    if isinstance(value, pd.Period):
        return str(value)
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def compute_chart(df: pd.DataFrame, chart: ChartSpec) -> dict:
    """Calcula los datos de un gráfico a partir del DataFrame normalizado.

    - kpi_card (dimension=None): aplica `aggregation` a `measure` y
      devuelve {"value": ...}.
    - Con `granularity`: convierte `dimension` al periodo correspondiente
      (día/semana/mes) antes de agrupar, y ordena cronológicamente.
    - bar/pie: ordena por valor descendente y limita a las 10 categorías
      principales.
    - Resto (line sin granularidad, table): agrupa por `dimension` en
      orden ascendente (orden por defecto de groupby).
    """
    if chart.measure not in df.columns:
        raise ValueError(f"La columna de medida '{chart.measure}' no existe en los datos")

    if chart.dimension is None:
        value = df[chart.measure].agg(chart.aggregation)
        return {"value": _to_native(value)}

    if chart.dimension not in df.columns:
        raise ValueError(f"La columna de dimensión '{chart.dimension}' no existe en los datos")

    work = df[[chart.dimension, chart.measure]].copy()

    if chart.granularity:
        work[chart.dimension] = pd.to_datetime(work[chart.dimension], errors="coerce")
        work = work.dropna(subset=[chart.dimension])
        work[chart.dimension] = work[chart.dimension].dt.to_period(_GRANULARITY_FREQ[chart.granularity])

    grouped = work.groupby(chart.dimension)[chart.measure].agg(chart.aggregation).reset_index()

    if chart.granularity:
        grouped = grouped.sort_values(chart.dimension)
    elif chart.chart_type in ("bar", "pie"):
        grouped = grouped.sort_values(chart.measure, ascending=False).head(10)

    data = [
        {"label": _to_native(row[chart.dimension]), "value": _to_native(row[chart.measure])}
        for _, row in grouped.iterrows()
    ]
    return {"data": data}


def compute_dashboard(df: pd.DataFrame, spec: DashboardSpec) -> dict:
    """Calcula los datos de cada gráfico de la spec.

    Si un gráfico falla (columna inexistente, etc.) se omite del resultado
    y se registra un warning, sin interrumpir el resto del dashboard.
    """
    result: dict = {}
    for chart in spec.charts:
        try:
            result[chart.id] = compute_chart(df, chart)
        except Exception as e:
            logger.warning("No se pudo calcular el gráfico '%s': %s", chart.id, e)
    return result

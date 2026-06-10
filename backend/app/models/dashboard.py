from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Literal


class ChartSpec(BaseModel):
    """Especificación declarativa de un único gráfico del dashboard."""

    id: str
    """Identificador único del gráfico dentro del dashboard."""

    title: str
    """Título legible mostrado encima del gráfico."""

    chart_type: Literal["line", "bar", "pie", "kpi_card", "table"]
    """Tipo de visualización a renderizar."""

    dimension: Optional[str] = None
    """Columna usada para agrupar los datos (eje X / categorías).
    Debe ser None cuando chart_type es "kpi_card"."""

    granularity: Optional[Literal["day", "week", "month"]] = None
    """Granularidad temporal de la dimensión, solo aplicable si la
    dimensión es una columna de tipo fecha/datetime."""

    measure: str
    """Columna sobre la que se calcula la métrica (eje Y / valor)."""

    aggregation: Literal["sum", "mean", "count", "min", "max"]
    """Función de agregación aplicada a la medida."""

    confidence: float = Field(ge=0.0, le=1.0)
    """Nivel de confianza (0-1) de que este gráfico es relevante y correcto."""

    rationale: str
    """Explicación de por qué se sugiere este gráfico para estos datos."""

    @model_validator(mode="after")
    def _kpi_card_has_no_dimension(self) -> "ChartSpec":
        if self.chart_type == "kpi_card" and self.dimension is not None:
            raise ValueError("kpi_card no debe tener dimension (debe ser None)")
        return self


class DashboardSpec(BaseModel):
    """Especificación declarativa de un dashboard completo."""

    charts: List[ChartSpec]
    """Lista de gráficos que componen el dashboard."""

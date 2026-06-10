import pandas as pd

from app.models.dashboard import ChartSpec, DashboardSpec
from app.services.claude_dashboard import validate_spec


def _df():
    return pd.DataFrame({
        "cantidad_fabricada": [10, 20, 30],
        "referencia_articulo": ["REF-1", "REF-2", "REF-3"],
        "fecha_orden_fabricacion": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
        "turno": ["turno_a", "turno_b", "turno_a"],
    })


def _kpi(id_, measure, aggregation):
    return ChartSpec(
        id=id_,
        title=id_,
        chart_type="kpi_card",
        dimension=None,
        measure=measure,
        aggregation=aggregation,
        confidence=1.0,
        rationale="test",
    )


def test_validate_spec_drops_hallucinated_column():
    df = _df()
    valid = _kpi("total_unidades", "cantidad_fabricada", "sum")
    hallucinated = ChartSpec(
        id="produccion_por_maquina",
        title="Producción por máquina",
        chart_type="bar",
        dimension="maquina_id",  # no existe en el dataset
        measure="cantidad_fabricada",
        aggregation="sum",
        confidence=0.5,
        rationale="test",
    )

    result = validate_spec(DashboardSpec(charts=[valid, hallucinated]), df)

    assert [c.id for c in result.charts] == ["total_unidades"]


def test_validate_spec_drops_sum_over_text_column():
    df = _df()
    valid = _kpi("total_unidades", "cantidad_fabricada", "sum")
    bad_sum = _kpi("suma_referencias", "referencia_articulo", "sum")

    result = validate_spec(DashboardSpec(charts=[valid, bad_sum]), df)

    assert [c.id for c in result.charts] == ["total_unidades"]


def test_validate_spec_drops_granularity_on_non_datetime_dimension():
    df = _df()
    valid = _kpi("total_unidades", "cantidad_fabricada", "sum")
    bad_granularity = ChartSpec(
        id="produccion_por_turno_mensual",
        title="Producción por turno (mensual)",
        chart_type="line",
        dimension="turno",  # no es de tipo fecha
        granularity="month",
        measure="cantidad_fabricada",
        aggregation="sum",
        confidence=0.5,
        rationale="test",
    )

    result = validate_spec(DashboardSpec(charts=[valid, bad_granularity]), df)

    assert [c.id for c in result.charts] == ["total_unidades"]


def test_validate_spec_keeps_valid_charts():
    df = _df()
    charts = [
        _kpi("total_unidades", "cantidad_fabricada", "sum"),
        ChartSpec(
            id="produccion_mensual",
            title="Producción mensual",
            chart_type="line",
            dimension="fecha_orden_fabricacion",
            granularity="month",
            measure="cantidad_fabricada",
            aggregation="sum",
            confidence=0.9,
            rationale="test",
        ),
        ChartSpec(
            id="produccion_por_turno",
            title="Producción por turno",
            chart_type="pie",
            dimension="turno",
            measure="cantidad_fabricada",
            aggregation="sum",
            confidence=0.8,
            rationale="test",
        ),
    ]

    result = validate_spec(DashboardSpec(charts=charts), df)

    assert [c.id for c in result.charts] == [c.id for c in charts]

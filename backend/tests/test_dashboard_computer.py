import pandas as pd

from app.models.dashboard import ChartSpec
from app.services.dashboard_computer import compute_chart


def test_kpi_card_sum():
    df = pd.DataFrame({"cantidad_fabricada": [10, 20, 30]})
    chart = ChartSpec(
        id="total_unidades",
        title="Total unidades fabricadas",
        chart_type="kpi_card",
        dimension=None,
        measure="cantidad_fabricada",
        aggregation="sum",
        confidence=1.0,
        rationale="test",
    )

    result = compute_chart(df, chart)

    assert result == {"value": 60}
    assert isinstance(result["value"], int)


def test_line_chart_monthly_granularity_sorted_chronologically():
    df = pd.DataFrame({
        "fecha_orden_fabricacion": pd.to_datetime(
            ["2024-03-01", "2024-01-15", "2024-01-20", "2024-02-10"]
        ),
        "cantidad_fabricada": [5, 10, 20, 7],
    })
    chart = ChartSpec(
        id="produccion_mensual",
        title="Producción mensual",
        chart_type="line",
        dimension="fecha_orden_fabricacion",
        granularity="month",
        measure="cantidad_fabricada",
        aggregation="sum",
        confidence=1.0,
        rationale="test",
    )

    result = compute_chart(df, chart)

    assert result["data"] == [
        {"label": "2024-01", "value": 30},
        {"label": "2024-02", "value": 7},
        {"label": "2024-03", "value": 5},
    ]


def test_bar_chart_sorted_descending_top10():
    # 12 categories with values 0..11 -> top 10 (2..11) descending, REF0/REF1 dropped
    df = pd.DataFrame({
        "referencia_articulo": [f"REF{i}" for i in range(12)],
        "cantidad_fabricada": list(range(12)),
    })
    chart = ChartSpec(
        id="produccion_por_referencia",
        title="Producción por referencia",
        chart_type="bar",
        dimension="referencia_articulo",
        measure="cantidad_fabricada",
        aggregation="sum",
        confidence=1.0,
        rationale="test",
    )

    result = compute_chart(df, chart)
    data = result["data"]
    values = [d["value"] for d in data]
    labels = [d["label"] for d in data]

    assert len(data) == 10
    assert values == sorted(values, reverse=True)
    assert values[0] == 11
    assert "REF0" not in labels
    assert "REF1" not in labels

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.dashboard import DashboardSpec
from app.services.dashboard_computer import compute_dashboard
from app.services.claude_dashboard import suggest_dashboard, validate_spec

router = APIRouter()


class DashboardDataRequest(BaseModel):
    columnas: list[str]
    filas: list[dict]
    spec: DashboardSpec


@router.post("/dashboard/data")
async def dashboard_data(body: DashboardDataRequest):
    """
    Recibe el dataset normalizado (mismo formato que devuelve /confirm:
    columnas + filas) junto con una DashboardSpec, y devuelve la spec
    junto con los datos calculados de cada gráfico.
    """
    df = pd.DataFrame(body.filas)
    cols = [c for c in body.columnas if c in df.columns]
    df = df[cols]

    data = compute_dashboard(df, body.spec)
    return {"spec": body.spec, "data": data}


class DashboardSuggestRequest(BaseModel):
    columnas: list[str]
    filas: list[dict]


@router.post("/dashboard/suggest")
async def dashboard_suggest(body: DashboardSuggestRequest):
    """
    Recibe el dataset normalizado (columnas + filas) y devuelve una
    DashboardSpec sugerida por Claude a partir de un perfil estadístico
    del dataset, validada contra las columnas y tipos reales.
    """
    df = pd.DataFrame(body.filas)
    cols = [c for c in body.columnas if c in df.columns]
    df = df[cols]

    if df.empty:
        raise HTTPException(status_code=400, detail="No hay datos para sugerir un dashboard")

    try:
        spec = suggest_dashboard(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando la sugerencia de dashboard: {str(e)}")

    spec = validate_spec(spec, df)
    return spec

# Dataplant — Contexto del proyecto

## Qué es esto

SaaS de dashboards de KPIs para empresas industriales pequeñas del sector metal (20-100 personas).
El problema: sus datos están en Excels caóticos y no pueden visualizar KPIs fácilmente.
La solución: suben el Excel → Claude mapea las columnas automáticamente → Python transforma → dashboard de KPIs.

## Estado actual

MVP funcional con el pipeline core:
- Upload de Excel → Claude mapea columnas → usuario revisa → Python transforma → tabla normalizada
- **Próximo paso: guardar datos normalizados en Supabase + dashboard de KPIs del metal**

## Arquitectura

```
Frontend (Next.js :3000)  →  Backend (FastAPI :8000)  →  Anthropic API
                                      ↓
                               Supabase (PostgreSQL + Storage) — pendiente de integrar
```

## Stack técnico

- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Backend**: FastAPI (Python) + pandas + openpyxl
- **IA**: Anthropic SDK — modelo `claude-sonnet-4-6`
- **BD**: Supabase (PostgreSQL en EU, RGPD) — pendiente
- **Ficheros**: Supabase Storage — pendiente
- **Deploy**: Railway (cuando esté listo para producción)

## Cómo funciona el pipeline IA

Claude NO genera código Python. Claude recibe cabeceras + 10 filas de muestra y devuelve un JSON de mapeo.
Python aplica las transformaciones de forma determinista usando ese JSON.

```
Excel completo → pandas lee → extrae {headers + 10 filas} → Claude → JSON mapeo
                                                                          ↓
                                                              Python aplica transformaciones
                                                              (rename, cast tipos, limpieza)
                                                                          ↓
                                                              DataFrame normalizado
```

El prompt del sistema (`backend/app/prompts.py`) conoce vocabulario del sector metal:
OEE, merma, colada, orden de fabricación, scrap, turno, operario, tiempo de ciclo, setup, rechazo.

## Estructura de archivos

```
dataplant/
├── CLAUDE.md                          ← este archivo
├── README.md                          ← instrucciones de instalación
├── backend/
│   ├── app/
│   │   ├── main.py                    ← FastAPI app + CORS
│   │   ├── prompts.py                 ← system prompt sector metal (CLAVE)
│   │   ├── api/upload.py              ← endpoints /upload y /confirm
│   │   ├── models/mapping.py          ← schemas Pydantic
│   │   └── services/
│   │       ├── excel_reader.py        ← lectura segura pandas, archivos temp
│   │       ├── claude_mapper.py       ← llama a Claude API
│   │       └── transformer.py        ← aplica JSON mapeo al DataFrame
│   ├── requirements.txt
│   └── .env                           ← ANTHROPIC_API_KEY (no commitear)
└── frontend/
    └── src/
        ├── app/page.tsx               ← página principal, gestiona 3 estados
        └── components/
            ├── UploadZone.tsx         ← drag & drop Excel
            ├── MappingReview.tsx      ← tabla editable, confianza por columna
            └── NormalizedTable.tsx    ← resultado final normalizado
```

## Endpoints del backend

| Método | Ruta | Qué hace |
|--------|------|----------|
| POST | `/api/upload` | Recibe .xlsx, llama a Claude, devuelve mapeo |
| POST | `/api/confirm` | Recibe mapeo confirmado, transforma, devuelve datos |
| GET | `/api/health` | Health check |

## Schema JSON que devuelve Claude

```json
{
  "columnas": [
    {
      "origen": "Ref_prod_v2",
      "destino": "referencia",
      "tipo": "string",
      "formato": null,
      "limpieza": null,
      "confianza": "alta",
      "nota": null
    },
    {
      "origen": "Scrap_%",
      "destino": "tasa_rechazo",
      "tipo": "float",
      "limpieza": "quitar_pct",
      "confianza": "alta",
      "nota": null
    }
  ],
  "schema_detectado": "ordenes_produccion"
]
```

Valores posibles:
- `tipo`: string | float | integer | date | boolean
- `limpieza`: quitar_pct | quitar_euro | strip | null
- `confianza`: alta | media | baja
- `schema_detectado`: ordenes_produccion | inventario | mantenimiento | calidad | otro

## KPIs del sector metal (para el dashboard — próxima fase)

Los KPIs que hay que calcular una vez los datos estén normalizados:
- **OEE** = Disponibilidad × Rendimiento × Calidad
- **Tasa de rechazo** = unidades_rechazadas / unidades_fabricadas × 100
- **Tiempo de ciclo medio** por referencia y por máquina
- **Producción por turno** (A / B / C)
- **Merma por orden de fabricación**
- **Rendimiento por máquina**

## Decisiones de diseño importantes

1. **Claude solo recibe muestra, nunca el archivo completo** — privacidad + coste de tokens
2. **El archivo Excel se guarda en /tmp durante la sesión** — se borra tras confirmar el mapeo
3. **Multi-tenant desde el principio** — cada empresa tendrá schema PostgreSQL separado
4. **El prompt mejora con ejemplos acumulados** — tabla `mapeos_confirmados` en Supabase (pendiente)
5. **Sin LangChain** — Anthropic SDK directa, más simple y más barato

## Contexto de negocio

- Clientes objetivo: fábricas metal 20-100 personas en España
- Precio: 79€ (Starter) / 149€ (Pro) / 299€ (Business) por mes
- Coste IA por cliente: ~0,50€/mes (insignificante)
- Infraestructura MVP: Railway + Supabase (~50€/mes total)
- Dos socios fundadores, recursos limitados, fase de validación

## Cómo arrancar en local

```bash
# Terminal 1 — backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev

# Abrir http://localhost:3000
# API docs en http://localhost:8000/docs
```

## Archivo de prueba

`produccion_junio2025_CAOTICO.xlsx` — Excel con datos caóticos del sector metal para probar el pipeline.
Contiene: fechas en 4 formatos distintos, porcentajes como texto, costes con/sin símbolo €,
cantidades con unidades, fila duplicada, totales en medio de los datos, 3 hojas.

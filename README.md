# Dataplant MVP

Pipeline: Excel → Claude (mapeo IA) → Python (transformación) → datos normalizados.

## Requisitos previos

- Python 3.11+
- Node.js 18+
- Cuenta en [console.anthropic.com](https://console.anthropic.com) con créditos (mínimo 5$)

---

## Instalación

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copia el archivo de variables de entorno:
```bash
cp .env.example .env
```

Edita `.env` y añade tu API key de Anthropic:
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 2. Frontend (Next.js)

```bash
cd frontend
npm install
```

---

## Arrancar en desarrollo

Necesitas dos terminales abiertas:

**Terminal 1 — Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Abre el navegador en [http://localhost:3000](http://localhost:3000)

La documentación automática de la API está en [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Cómo funciona

1. El usuario sube un `.xlsx` desde la interfaz
2. FastAPI lo lee con pandas (sin ejecutar macros)
3. Se envían solo las **cabeceras + 10 filas** a Claude — nunca el archivo completo
4. Claude devuelve un JSON con el mapeo de columnas y nivel de confianza
5. El usuario puede revisar y corregir el mapeo antes de confirmar
6. Python aplica las transformaciones (renombrar, convertir tipos, limpiar) al archivo completo
7. Se muestra la tabla normalizada
8. El usuario pulsa "Generar dashboard": se envía un **perfil estadístico** de la tabla
   normalizada (tipos, % de nulos, min/max, valores más frecuentes — nunca las filas) a Claude,
   que propone entre 4 y 6 gráficos (KPIs, series temporales, barras, circulares)
9. El backend valida la propuesta contra los datos reales y descarta gráficos que referencien
   columnas inexistentes o agregaciones inválidas. Si no queda ningún gráfico válido, se informa
   al usuario y puede construir el dashboard manualmente desde cero
10. El usuario revisa y ajusta cada gráfico (título, tipo, dimensión, medida, agregación,
    granularidad), puede excluir o eliminar gráficos y añadir otros nuevos
11. Al confirmar, Python calcula los datos de cada gráfico sobre la tabla normalizada y se
    renderiza el dashboard final con Recharts

---

## Estructura del proyecto

```
dataplant/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app
│   │   ├── prompts.py                 # System prompts (mapeo + dashboard) sector metal
│   │   ├── api/
│   │   │   ├── upload.py              # Endpoints /upload y /confirm
│   │   │   └── dashboard.py           # Endpoints /dashboard/suggest y /dashboard/data
│   │   ├── models/
│   │   │   ├── mapping.py             # Schemas Pydantic del mapeo de columnas
│   │   │   └── dashboard.py           # Schemas Pydantic de la spec del dashboard (ChartSpec, DashboardSpec)
│   │   └── services/
│   │       ├── excel_reader.py        # Lectura segura con pandas
│   │       ├── claude_mapper.py       # Llamada a Claude para el mapeo de columnas
│   │       ├── transformer.py         # Transformaciones pandas
│   │       ├── claude_dashboard.py    # Perfilado de datos + sugerencia/validación del dashboard con Claude
│   │       └── dashboard_computer.py  # Cálculo (pandas) de los datos de cada gráfico
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── src/
        ├── app/page.tsx              # Página principal (máquina de estados)
        └── components/
            ├── UploadZone.tsx        # Drag & drop
            ├── MappingReview.tsx     # Tabla editable de mapeo
            ├── NormalizedTable.tsx   # Resultado normalizado
            ├── DashboardReview.tsx   # Revisión/edición de los gráficos sugeridos
            └── Dashboard.tsx         # Renderizado del dashboard final (Recharts)
```

---

## Próximos pasos (v2)

- [ ] Guardar datos normalizados en PostgreSQL (Supabase)
- [ ] Auth de usuarios (Supabase Auth)
- [ ] Base de ejemplos aprendidos para mejorar el mapeo automático
- [ ] Dashboard de KPIs del sector metal
- [ ] Deploy en Railway

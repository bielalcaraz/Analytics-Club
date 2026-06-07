import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import tempfile
import pandas as pd
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "backend" / ".env")

from app.services.excel_reader import read_excel_safe, extract_sample
from app.services.claude_mapper import map_columns_with_claude
from app.services.transformer import apply_mapping
from app.models.mapping import MappingResult, ColumnMapping

st.set_page_config(page_title="Dataplant — Pipeline test", layout="wide")
st.title("Dataplant — Prueba del pipeline")
st.caption("Upload Excel → Claude mapea columnas → Python transforma")

# ── Estado de sesión ─────────────────────────────────────────────────────────
for key in ("df_full", "mapping", "df_normalized", "sample_info", "sheet_names"):
    if key not in st.session_state:
        st.session_state[key] = None


def reset():
    for key in ("df_full", "mapping", "df_normalized", "sample_info", "sheet_names"):
        st.session_state[key] = None


def safe_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas object a str para evitar errores de Arrow/pyarrow."""
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].astype(str).replace("nan", "")
    return out


# ── PASO 1: Subir Excel ──────────────────────────────────────────────────────
st.header("1  Subir Excel")

uploaded = st.file_uploader("Arrastra tu .xlsx aquí", type=["xlsx", "xls"])

if uploaded:
    if st.session_state.df_full is None:
        # Guardar en temp para que pandas pueda leer
        suffix = Path(uploaded.name).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = Path(tmp.name)

        # Detectar hojas disponibles
        import openpyxl
        wb = openpyxl.load_workbook(tmp_path, read_only=True, data_only=True)
        st.session_state.sheet_names = wb.sheetnames
        wb.close()

        # Si hay varias hojas, que el usuario elija
        if len(st.session_state.sheet_names) > 1:
            sheet = st.selectbox(
                f"El archivo tiene {len(st.session_state.sheet_names)} hojas — ¿cuál usar?",
                st.session_state.sheet_names,
            )
        else:
            sheet = st.session_state.sheet_names[0]

        if st.button("Cargar hoja", type="primary"):
            with st.spinner("Leyendo Excel..."):
                df = pd.read_excel(tmp_path, sheet_name=sheet, engine="openpyxl", nrows=10000)
                st.session_state.df_full = df
                st.session_state.sample_info = extract_sample(df)
            os.unlink(tmp_path)
            st.rerun()
        else:
            os.unlink(tmp_path)
            st.stop()
    else:
        df = st.session_state.df_full
        st.success(f"Excel cargado — {len(df)} filas · {len(df.columns)} columnas")
        with st.expander("Vista previa (10 primeras filas)"):
            st.dataframe(safe_dataframe(df.head(10)), use_container_width=True)

# ── PASO 2: Mapeo con Claude ──────────────────────────────────────────────────
if st.session_state.df_full is not None:
    st.divider()
    st.header("2  Mapeo con Claude")

    if st.session_state.mapping is None:
        if st.button("Analizar columnas con Claude", type="primary"):
            sample = st.session_state.sample_info
            with st.spinner("Claude analizando columnas..."):
                try:
                    mapping = map_columns_with_claude(sample["headers"], sample["sample_rows"])
                    st.session_state.mapping = mapping
                    st.rerun()
                except Exception as e:
                    st.error(f"Error llamando a Claude: {e}")
    else:
        mapping: MappingResult = st.session_state.mapping

        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.info(f"Schema detectado: **{mapping.schema_detectado}**")
        with col_b:
            if st.button("Re-analizar"):
                st.session_state.mapping = None
                st.session_state.df_normalized = None
                st.rerun()

        # Tabla de mapeo con colores por confianza
        CONF_COLORS = {"alta": "🟢", "media": "🟡", "baja": "🔴"}
        rows = [
            {
                "": CONF_COLORS.get(c.confianza, ""),
                "Columna original": c.origen,
                "→ Nombre destino": c.destino,
                "Tipo": c.tipo,
                "Limpieza": c.limpieza or "—",
                "Confianza": c.confianza,
                "Nota": c.nota or "—",
            }
            for c in mapping.columnas
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        baja = [c for c in mapping.columnas if c.confianza == "baja"]
        media = [c for c in mapping.columnas if c.confianza == "media"]
        if baja:
            st.warning(f"{len(baja)} columna(s) con confianza **baja** — revisa antes de continuar.")
        elif media:
            st.info(f"{len(media)} columna(s) con confianza **media**.")

# ── PASO 3: Transformar ───────────────────────────────────────────────────────
if st.session_state.mapping is not None:
    st.divider()
    st.header("3  Transformar datos")

    if st.session_state.df_normalized is None:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirmar mapeo y transformar", type="primary"):
                with st.spinner("Aplicando transformaciones con pandas..."):
                    try:
                        df_norm = apply_mapping(st.session_state.df_full, st.session_state.mapping)
                        st.session_state.df_normalized = df_norm
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error en la transformación: {e}")
        with c2:
            if st.button("Empezar de nuevo"):
                reset()
                st.rerun()
    else:
        df_norm = st.session_state.df_normalized

        st.success(
            f"Transformación completada — {len(df_norm)} filas · {len(df_norm.columns)} columnas normalizadas"
        )
        st.dataframe(safe_dataframe(df_norm), use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            csv = df_norm.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Descargar CSV normalizado",
                data=csv,
                file_name="datos_normalizados.csv",
                mime="text/csv",
            )
        with c2:
            if st.button("Nueva prueba"):
                reset()
                st.rerun()

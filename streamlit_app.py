import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import re
import tempfile
import pandas as pd
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "backend" / ".env")

from app.services.excel_reader import read_excel_safe, extract_sample, clean_structural_rows
from app.services.claude_mapper import map_columns_with_claude
from app.services.transformer import apply_mapping_with_warnings, _PERSON_COLS
from app.services.text_normalizer import detect_person_groups
from app.models.mapping import MappingResult, ColumnMapping

st.set_page_config(page_title="Dataplant — Pipeline test", layout="wide")
st.title("Dataplant — Prueba del pipeline")
st.caption("Upload Excel → Claude mapea columnas → Python transforma")

# ── Estado de sesión ─────────────────────────────────────────────────────────
SESSION_KEYS = ("df_full", "mapping", "df_normalized", "sample_info",
                "sheet_names", "duplicates_df", "df_with_selection", "normalizaciones",
                "posibles_duplicados", "grupos_personas", "grupos_referencias")
for key in SESSION_KEYS:
    if key not in st.session_state:
        st.session_state[key] = None


def reset():
    for key in SESSION_KEYS:
        st.session_state[key] = None


def safe_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d").where(out[col].notna(), "")
        elif out[col].dtype == object:
            out[col] = out[col].astype(str).replace("nan", "")
    return out


def detect_duplicates(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Devuelve las filas duplicadas (todas las ocurrencias) o None si no hay.
    Ignora columnas de texto libre (observaciones, notas) para detectar
    duplicados que solo difieren en ese campo.
    """
    FREE_TEXT = re.compile(r"observ|nota|comentar|descripci|remark", re.IGNORECASE)
    key_cols = [c for c in df.columns if not FREE_TEXT.search(c)]
    if not key_cols:
        key_cols = df.columns.tolist()

    mask = df.duplicated(subset=key_cols, keep=False)
    return df[mask].copy() if mask.any() else None


# ── PASO 1: Subir Excel ──────────────────────────────────────────────────────
st.header("1  Subir Excel")

uploaded = st.file_uploader("Arrastra tu .xlsx aquí", type=["xlsx", "xls"])

if uploaded:
    if st.session_state.df_full is None:
        suffix = Path(uploaded.name).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = Path(tmp.name)

        import openpyxl
        wb = openpyxl.load_workbook(tmp_path, read_only=True, data_only=True)
        st.session_state.sheet_names = wb.sheetnames
        wb.close()

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
                df = clean_structural_rows(df)
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
                st.session_state.duplicates_df = None
                st.rerun()

        CONF_COLORS = {"alta": "🟢", "media": "🟡", "baja": "🔴"}
        rows = [
            {
                "": CONF_COLORS.get(c.confianza, ""),
                "Columna original": c.origen,
                "→ Nombre destino": c.destino,
                "Tipo": c.tipo,
                "Limpieza": c.limpieza or "—",
                "Valores norm.": f"{len(c.valores)} valores" if c.valores else "—",
                "Separa unidad": "✓" if getattr(c, "extraer_unidad", None) else "—",
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

    # 3a — Botón de transformación
    if st.session_state.df_normalized is None:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirmar mapeo y transformar", type="primary"):
                with st.spinner("Aplicando transformaciones y normalizando texto con Claude..."):
                    try:
                        df_result, warnings, normalizaciones, posibles_duplicados = (
                            apply_mapping_with_warnings(
                                st.session_state.df_full, st.session_state.mapping
                            )
                        )
                        df_result = df_result.round(6)
                        st.session_state.df_normalized = df_result
                        st.session_state.duplicates_df = detect_duplicates(df_result)
                        st.session_state.normalizaciones = normalizaciones
                        st.session_state.posibles_duplicados = posibles_duplicados
                        for w in warnings:
                            st.warning(w)

                        # Detectar grupos de nombres de personas
                        grupos = []
                        for col in st.session_state.mapping.columnas:
                            if col.tipo != "string":
                                continue
                            dest = col.destino
                            if dest not in df_result.columns:
                                continue
                            if not any(kw in dest.lower() for kw in _PERSON_COLS):
                                continue
                            unique_vals = [
                                str(v) for v in df_result[dest].dropna().unique()
                                if str(v) not in ("", "nan", "None")
                            ]
                            if len(unique_vals) >= 2:
                                grupos.extend(detect_person_groups(dest, unique_vals))
                        st.session_state.grupos_personas = grupos

                        # Convertir posibles_duplicados a formato interactivo
                        grupos_refs = []
                        for col_name, groups in posibles_duplicados.items():
                            for group in groups:
                                if len(group) >= 2:
                                    grupos_refs.append({
                                        "column_name": col_name,
                                        "valores": list(group),
                                        "nombre_canonico": group[0],
                                        "confianza": "media",
                                    })
                        st.session_state.grupos_referencias = grupos_refs

                        st.rerun()
                    except Exception as e:
                        st.error(f"Error en la transformación: {e}")
        with c2:
            if st.button("Empezar de nuevo"):
                reset()
                st.rerun()

    # 3b — Revisión combinada: personas + referencias de artículo
    _gp = st.session_state.grupos_personas or []
    _gr = st.session_state.grupos_referencias or []

    if _gp or _gr:
        total = len(_gp) + len(_gr)
        st.subheader(f"Revisión de posibles duplicados — {total} grupo(s)")
        st.info("Confirma cuáles son la misma entidad. Solo se unificarán los grupos que apruebes.")

        # ── Nombres de personas ──────────────────────────────────────────────
        if _gp:
            st.markdown("#### 👤 Nombres de personas")
            for i, grupo in enumerate(_gp):
                with st.container(border=True):
                    col_tag, col_conf = st.columns([3, 1])
                    with col_tag:
                        st.markdown(
                            f"Columna **`{grupo['column_name']}`** — "
                            "¿estas entradas son la misma persona?"
                        )
                    with col_conf:
                        st.caption(f"confianza: {grupo['confianza']}")
                    st.markdown(" · ".join(f"`{v}`" for v in grupo["valores"]))
                    col_check, col_sel = st.columns([1, 3])
                    with col_check:
                        st.checkbox("Sí, unificar", value=True, key=f"persona_approve_{i}")
                    with col_sel:
                        if st.session_state.get(f"persona_approve_{i}", True):
                            st.selectbox(
                                "Nombre final:",
                                options=grupo["valores"],
                                index=grupo["valores"].index(grupo["nombre_canonico"]),
                                key=f"persona_canonico_{i}",
                            )

        # ── Referencias de artículo ──────────────────────────────────────────
        if _gr:
            if _gp:
                st.divider()
            st.markdown("#### 🔖 Referencias de artículo")
            for i, grupo in enumerate(_gr):
                with st.container(border=True):
                    col_tag, col_conf = st.columns([3, 1])
                    with col_tag:
                        st.markdown(
                            f"Columna **`{grupo['column_name']}`** — "
                            "¿estas referencias son el mismo artículo?"
                        )
                    with col_conf:
                        st.caption(f"confianza: {grupo['confianza']}")
                    st.markdown(" · ".join(f"`{v}`" for v in grupo["valores"]))
                    col_check, col_sel = st.columns([1, 3])
                    with col_check:
                        st.checkbox("Sí, unificar", value=True, key=f"ref_approve_{i}")
                    with col_sel:
                        if st.session_state.get(f"ref_approve_{i}", True):
                            st.selectbox(
                                "Referencia final:",
                                options=grupo["valores"],
                                index=0,
                                key=f"ref_canonico_{i}",
                            )

        st.divider()
        col_a, col_b = st.columns([2, 1])
        with col_a:
            if st.button("Aplicar cambios confirmados", type="primary"):
                df = st.session_state.df_normalized

                for i, grupo in enumerate(_gp):
                    if st.session_state.get(f"persona_approve_{i}", True):
                        canonico = st.session_state.get(f"persona_canonico_{i}", grupo["nombre_canonico"])
                        repl = {v: canonico for v in grupo["valores"] if v != canonico}
                        if repl:
                            df[grupo["column_name"]] = df[grupo["column_name"]].replace(repl)

                for i, grupo in enumerate(_gr):
                    if st.session_state.get(f"ref_approve_{i}", True):
                        canonico = st.session_state.get(f"ref_canonico_{i}", grupo["valores"][0])
                        repl = {v: canonico for v in grupo["valores"] if v != canonico}
                        if repl:
                            df[grupo["column_name"]] = df[grupo["column_name"]].replace(repl)

                for i in range(len(_gp)):
                    st.session_state.pop(f"persona_approve_{i}", None)
                    st.session_state.pop(f"persona_canonico_{i}", None)
                for i in range(len(_gr)):
                    st.session_state.pop(f"ref_approve_{i}", None)
                    st.session_state.pop(f"ref_canonico_{i}", None)

                st.session_state.df_normalized = df
                st.session_state.grupos_personas = []
                st.session_state.grupos_referencias = []
                st.session_state.posibles_duplicados = {}
                st.rerun()

        with col_b:
            if st.button("Omitir todo"):
                for i in range(len(_gp)):
                    st.session_state.pop(f"persona_approve_{i}", None)
                    st.session_state.pop(f"persona_canonico_{i}", None)
                for i in range(len(_gr)):
                    st.session_state.pop(f"ref_approve_{i}", None)
                    st.session_state.pop(f"ref_canonico_{i}", None)
                st.session_state.grupos_personas = []
                st.session_state.grupos_referencias = []
                st.rerun()

        st.stop()

    # 3c — Resultado final
    if st.session_state.df_normalized is not None:
        df_norm = st.session_state.df_normalized
        dups: pd.DataFrame | None = st.session_state.duplicates_df

        # ── Revisión de duplicados (antes de la tabla y la descarga) ─────
        if dups is not None:
            n_grupos = len(dups) - dups.duplicated(keep="first").sum()
            st.subheader("⚠️ Revisión de filas duplicadas")
            st.warning(
                f"Se detectaron **{len(dups)} filas** que aparecen más de una vez, "
                f"formando **{n_grupos} grupo(s)** de duplicados. "
                "Revísalas antes de descargar. Por defecto solo se marca la copia extra — "
                "la primera ocurrencia se conserva. Ajusta las marcas según necesites y pulsa **Aplicar**."
            )

            # Pre-marcar solo las copias extra (keep="first" → primera ocurrencia = False)
            dup_editor_df = safe_dataframe(dups).copy()
            dup_editor_df.insert(0, "Eliminar", dups.duplicated(keep="first").values)

            edited_dups = st.data_editor(
                dup_editor_df,
                use_container_width=True,
                hide_index=False,
                key="dup_editor",
                column_config={
                    "Eliminar": st.column_config.CheckboxColumn(
                        "Eliminar",
                        help="Filas marcadas se eliminarán al pulsar Aplicar",
                        default=False,
                    )
                },
            )

            n_eliminar = int(edited_dups["Eliminar"].sum())
            c_d1, c_d2 = st.columns([2, 1])
            with c_d1:
                if st.button(
                    f"Aplicar — eliminar {n_eliminar} fila(s) marcada(s)",
                    type="primary",
                    disabled=(n_eliminar == 0),
                ):
                    indices_eliminar = edited_dups[edited_dups["Eliminar"] == True].index.tolist()
                    df_clean = df_norm.drop(index=indices_eliminar).reset_index(drop=True)
                    st.session_state.df_normalized = df_clean
                    st.session_state.duplicates_df = None
                    st.rerun()
            with c_d2:
                if st.button("Ignorar y conservar todas"):
                    st.session_state.duplicates_df = None
                    st.rerun()

            st.divider()

        # Referencias similares
        posibles_dup = st.session_state.posibles_duplicados
        if posibles_dup:
            with st.expander(
                f"⚠️ Referencias posiblemente duplicadas ({sum(len(g) for g in posibles_dup.values())} grupo(s))",
                expanded=True,
            ):
                st.caption(
                    "Estas referencias podrían ser la misma pieza — verifica con tu equipo antes de usar los datos."
                )
                for col_name, groups in posibles_dup.items():
                    for group in groups:
                        st.markdown(f"**{col_name}**: " + " / ".join(f"`{v}`" for v in group))

        st.success(
            f"Transformación completada — {len(df_norm)} filas · {len(df_norm.columns)} columnas normalizadas"
        )

        norm = st.session_state.normalizaciones
        if norm:
            with st.expander(f"Texto normalizado por IA ({len(norm)} columna(s))", expanded=False):
                for col_name, changes in norm.items():
                    partes = " · ".join(f"`{orig}` → `{dest}`" for orig, dest in changes.items())
                    st.markdown(f"**{col_name}**: {partes}")

        st.dataframe(safe_dataframe(df_norm), use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            csv = df_norm.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8")
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

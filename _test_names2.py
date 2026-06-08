import sys
sys.path.insert(0, "backend")

import pandas as pd
import unittest.mock as mock
from app.services.transformer import _safe_map, _PERSON_COLS, _SKIP_NORM, _normalize_text_columns
from app.models.mapping import MappingResult, ColumnMapping

all_ok = True

print("=== _safe_map: validacio longitud (aplicat a totes les columnes) ===")
cases = [
    # (orig, norm, expected, description)
    ("Pedro G.",    "Pedro Garcia",  "Pedro G.",     "diff=6 > 3 -> revert"),
    ("Pedro G.",    "Pedro Garcia",  "Pedro G.",     "diff=8 > 3 -> revert"),
    ("P.Garcia",    "P. Garcia",     "P. Garcia",    "diff=1 <= 3 -> keep"),
    ("MARTINEZ J.", "Martinez J.",   "Martinez J.",  "diff=0 -> keep"),
    ("bloq.",       "bloqueada",     "bloq.",        "diff=4 > 3 -> revert"),
    ("ok",          "completada",    "ok",           "diff=6 > 3 -> revert"),
    ("en curso",    "en_curso",      "en_curso",     "diff=0 underscore -> keep"),
]
for orig, norm, expected, desc in cases:
    got = _safe_map(orig, norm)
    ok = got == expected
    if not ok:
        all_ok = False
    print(f"  [{'OK' if ok else 'FAIL'}] {desc}: '{orig}' -> '{got}' (exp '{expected}')")

print()
print("=== Columnes persona: skip Claude, aplica .str.title() ===")
mapping = MappingResult(
    schema_detectado="calidad",
    columnas=[
        ColumnMapping(origen="insp",   destino="inspector",       tipo="string", confianza="alta"),
        ColumnMapping(origen="op",     destino="nombre_operario", tipo="string", confianza="alta"),
        ColumnMapping(origen="tipus",  destino="tipo_defecto",    tipo="string", confianza="alta"),
    ]
)
df = pd.DataFrame({
    "inspector":       ["PEDRO G.", "p.garcia",  "MARTINEZ J."],
    "nombre_operario": ["JUAN M.",  "juan m.",   "JUAN M."],
    "tipo_defecto":    ["Raya",     "RAYA",      "Aranhazo"],
})

with mock.patch("app.services.transformer.normalize_free_text",
                return_value={"Raya": "raya", "RAYA": "raya", "Aranhazo": "aranhazo"}) as mocked:
    result_df, changes = _normalize_text_columns(df.copy(), mapping)

    # Inspector i nombre_operario NO han de cridar Claude
    person_calls = [c for c in mocked.call_args_list
                    if "inspector" in str(c) or "operario" in str(c)]
    ok = len(person_calls) == 0
    if not ok:
        all_ok = False
    print(f"  [{'OK' if ok else 'FAIL'}] Claude NO cridat per columnes persona")

    # title case: Python .title() capitalitza despres de punt i espai
    # "PEDRO G." -> "Pedro G.", "p.garcia" -> "P.Garcia", "MARTINEZ J." -> "Martinez J."
    expected_insp = ["Pedro G.", "P.Garcia", "Martinez J."]
    got_insp = result_df["inspector"].tolist()
    ok = got_insp == expected_insp
    if not ok:
        all_ok = False
    print(f"  [{'OK' if ok else 'FAIL'}] inspector title case: {got_insp} (exp {expected_insp})")

    # tipo_defecto SI passa per Claude (no es persona ni ID)
    tipo_calls = [c for c in mocked.call_args_list if "tipo_defecto" in str(c)]
    ok = len(tipo_calls) == 1
    if not ok:
        all_ok = False
    print(f"  [{'OK' if ok else 'FAIL'}] Claude cridat per tipo_defecto ({len(tipo_calls)} crida/es)")

print()
print("=== _PERSON_COLS i _SKIP_NORM: keywords corrects ===")
person_tests = [
    ("inspector",           True),
    ("nombre_inspector",    True),
    ("tecnico",             True),
    ("nombre_tecnico",      True),
    ("operario",            True),
    ("nombre_operario",     True),
    ("responsable",         True),
    ("tecnico_responsable", True),
    ("tipo_defecto",        False),
    ("estado_pedido",       False),
]
for col, expected in person_tests:
    is_person = any(kw in col.lower() for kw in _PERSON_COLS)
    ok = is_person == expected
    if not ok:
        all_ok = False
    print(f"  [{'OK' if ok else 'FAIL'}] '{col}': persona={is_person} (exp {expected})")

print()
skip_tests = [
    ("numero_orden",    True,  "conté 'orden'"),
    ("codigo_articulo", True,  "conté 'codigo'"),
    ("referencia",      True,  "conté 'referencia'"),
    ("descripcion",     True,  "conté 'descripcion'"),
    ("estado_stock",    False, "no conté cap keyword skip"),
    ("tipo_defecto",    False, "no conté cap keyword skip"),
    ("turno",           False, "no conté cap keyword skip"),
]
for col, expected, reason in skip_tests:
    is_skip = any(kw in col.lower() for kw in _SKIP_NORM)
    ok = is_skip == expected
    if not ok:
        all_ok = False
    print(f"  [{'OK' if ok else 'FAIL'}] '{col}' skip={is_skip} (exp {expected}) — {reason}")

print()
print("Result:", "PASS" if all_ok else "FAIL")

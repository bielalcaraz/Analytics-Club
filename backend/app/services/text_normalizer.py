import json
import anthropic

SYSTEM_PROMPT_NORMALIZER = """Eres un experto en datos de fabricación metálica. Tu tarea es \
normalizar valores de texto libre de una columna de datos industriales. Devuelve ÚNICAMENTE \
un JSON válido sin texto adicional, donde cada clave es el valor original y el valor es \
su forma normalizada.

Reglas generales:
- Agrupa sinónimos y variaciones del mismo concepto bajo un único valor normalizado
- Mantén el significado industrial: 'bloq.' y 'Bloqueada' son la misma cosa, normaliza a 'bloqueada'
- Para estados de órdenes de fabricación usa siempre:
  completada | en_curso | bloqueada | pendiente | cancelada
- Para turnos usa siempre: turno_a | turno_b | turno_c | turno_manana | turno_tarde | turno_noche
- Para resultados de calidad usa siempre: ok | nok | pendiente
- Si no puedes determinar el significado con certeza, devuelve el valor tal cual

Regla especial para NOMBRES DE EMPRESA Y PROVEEDOR:
- Usa Title Case (primera letra de cada palabra en mayúscula), NO snake_case ni minúsculas
- Agrupa variantes del mismo proveedor bajo el nombre más completo disponible
- Ejemplo: 'ACEROS BCN', 'Aceros BCN S.L.', 'aceros bcn' → 'Aceros BCN S.L.'
- Ejemplo: 'METALPRO', 'MetalPro S.A.', 'metalpro sa' → 'MetalPro S.A.'
- Conserva siglas jurídicas si aparecen en alguna variante: S.L., S.A., S.L.U., etc.

Regla especial para NOMBRES DE PERSONAS (operario, inspector, técnico, responsable):
- NUNCA completes ni inventes apellidos a partir de iniciales.
  'Pedro G.' → 'Pedro G.' (no puedes saber si es García, González o Gutiérrez)
  'P.Garcia' → 'P. Garcia' (solo añadir espacio tras el punto)
  'MARTINEZ J.' → 'Martinez J.' (solo corregir capitalización)
- Solo puedes: corregir capitalización, añadir espacio tras punto, eliminar espacios dobles.
- Si dos valores podrían ser la misma persona pero no estás seguro al 100%, \
devuelve cada uno tal cual — no los unifiques.
- El valor normalizado NUNCA debe ser más largo que el original.

- NUNCA modifiques códigos de producto, referencias de artículo, IDs de máquina, números de orden \
ni cualquier valor alfanumérico que parezca un código técnico (contiene guiones con números o \
letras en mayúsculas tipo TRN-04, VLV-DN50, OF-2841). Solo normaliza campos semánticos como \
estados, resultados, categorías, nombres de empresa y descripciones de texto libre."""


def normalize_free_text(column_name: str, unique_values: list[str]) -> dict:
    """
    Segunda llamada a Claude para normalizar valores de texto libre.
    Recibe el nombre de columna y sus valores únicos (no todas las filas).
    Devuelve {valor_original: valor_normalizado} o {} si falla.
    """
    if len(unique_values) < 2:
        return {}

    try:
        client = anthropic.Anthropic()

        user_message = (
            f"Columna: {column_name}\n"
            f"Valores únicos encontrados: {json.dumps(unique_values, ensure_ascii=False)}\n\n"
            "Devuelve el JSON de normalización."
        )

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=SYSTEM_PROMPT_NORMALIZER,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        raw_dict = json.loads(raw)
        return {str(k): str(v) if v is not None else None for k, v in raw_dict.items()}

    except Exception:
        return {}

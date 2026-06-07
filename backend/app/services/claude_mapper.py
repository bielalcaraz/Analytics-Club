import json
import anthropic
from app.prompts import SYSTEM_PROMPT_METAL
from app.models.mapping import MappingResult


def map_columns_with_claude(headers: list, sample_rows: list) -> MappingResult:
    """
    Envía cabeceras y muestra a Claude y recibe el mapeo en JSON.
    Solo se envían cabeceras + 10 filas — nunca el archivo completo.
    """
    client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno

    # Construir mensaje con contexto mínimo necesario
    user_message = f"""Analiza las siguientes columnas de un Excel industrial y devuelve el mapeo JSON.

Cabeceras encontradas: {json.dumps(headers, ensure_ascii=False)}

Muestra de datos (primeras filas):
{json.dumps(sample_rows[:10], ensure_ascii=False, default=str)}

Recuerda: devuelve ÚNICAMENTE el JSON, sin texto adicional."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT_METAL,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()

    # Limpiar por si Claude añade backticks accidentalmente
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    data = json.loads(raw)
    return MappingResult(**data)

# agent/brain.py — Cerebro del agente: conexión con Claude API
# Generado por AgentKit

"""
Lógica de IA del agente. Lee el system prompt de prompts.yaml, le da acceso
a las herramientas de The Nail Society Spa (catálogo, disponibilidad real y
agendado de citas) y genera respuestas usando la API de Anthropic Claude.
"""

import os
import json
import yaml
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from agent.tools import TOOLS_CLAUDE, ejecutar_herramienta
from agent.memory import obtener_configuracion

load_dotenv()
logger = logging.getLogger("agentkit")

# Cliente de Anthropic
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Límite de vueltas de uso de herramientas por mensaje (evita loops infinitos)
MAX_ITERACIONES_TOOLS = 5

# Zona horaria del negocio (Aguascalientes). Se usa para que el agente
# sepa la fecha/hora real al interpretar "hoy", "mañana", "el viernes", etc.
ZONA_HORARIA = ZoneInfo("America/Mexico_City")

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def construir_contexto_temporal() -> str:
    """
    Genera un bloque de contexto con la fecha y hora actual en la zona horaria
    del negocio. Se añade al system prompt en cada llamada para que el agente
    pueda calcular fechas reales al agendar citas y nunca las invente.
    """
    ahora = datetime.now(ZONA_HORARIA)
    dia = DIAS_SEMANA[ahora.weekday()]
    return (
        "## Fecha y hora actual (referencia obligatoria)\n"
        f"Hoy es {dia}, {ahora.day} de {MESES[ahora.month - 1]} de {ahora.year}.\n"
        f"Fecha de hoy en formato ISO: {ahora.strftime('%Y-%m-%d')}.\n"
        f"Hora local de Aguascalientes: {ahora.strftime('%H:%M')}.\n"
        "Usa SIEMPRE esta fecha como referencia para interpretar expresiones como "
        "\"hoy\", \"mañana\", \"pasado mañana\", \"el viernes\" o \"la próxima semana\". "
        "Al agendar una cita, calcula la fecha exacta en formato YYYY-MM-DD a partir de aquí. "
        "NUNCA inventes ni asumas una fecha distinta a la que se deduce de este dato."
    )


def cargar_config_prompts() -> dict:
    """Lee toda la configuración desde config/prompts.yaml."""
    try:
        with open("config/prompts.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error("config/prompts.yaml no encontrado")
        return {}


def cargar_system_prompt() -> str:
    """Lee el system prompt desde config/prompts.yaml."""
    config = cargar_config_prompts()
    return config.get("system_prompt", "Eres un asistente útil. Responde en español.")


def obtener_mensaje_error() -> str:
    """Retorna el mensaje de error configurado en prompts.yaml."""
    config = cargar_config_prompts()
    return config.get("error_message", "Lo siento, estoy teniendo problemas técnicos. Por favor intenta de nuevo en unos minutos.")


def obtener_mensaje_fallback() -> str:
    """Retorna el mensaje de fallback configurado en prompts.yaml."""
    config = cargar_config_prompts()
    return config.get("fallback_message", "Disculpa, no entendí tu mensaje. ¿Podrías reformularlo?")


def componer_system_prompt(config_db: dict) -> str:
    """Base de identidad desde prompts.yaml + capa editable desde la BD (anuncios,
    promociones e instrucciones extra que el salón administra desde el panel).
    Si la config de BD está vacía, el resultado es idéntico al de prompts.yaml."""
    partes = [cargar_system_prompt()]
    anuncios = (config_db.get("anuncios") or "").strip()
    if anuncios:
        partes.append("## Anuncios y promociones vigentes (información prioritaria y actual)\n" + anuncios)
    extra = (config_db.get("instrucciones_extra") or "").strip()
    if extra:
        partes.append("## Instrucciones adicionales del negocio\n" + extra)
    return "\n\n".join(partes)


async def generar_respuesta(mensaje: str, historial: list[dict], telefono: str) -> str:
    """
    Genera una respuesta usando Claude API, permitiendo el uso de herramientas
    (búsqueda en knowledge y agendado de citas).

    Args:
        mensaje: El mensaje nuevo del usuario
        historial: Lista de mensajes anteriores [{"role": "user/assistant", "content": "..."}]
        telefono: Número de teléfono del cliente (para asociar citas)

    Returns:
        La respuesta generada por Claude
    """
    # Configuración editable del negocio (BD). Si falla la lectura, se usa lo de
    # prompts.yaml — el bot nunca deja de responder por un problema de config.
    config_db = {}
    try:
        config_db = await obtener_configuracion()
    except Exception as e:
        logger.error(f"No se pudo leer la configuración del negocio: {e}")
    fallback = (config_db.get("fallback_message") or "").strip() or obtener_mensaje_fallback()
    error_msg = (config_db.get("error_message") or "").strip() or obtener_mensaje_error()

    # Si el mensaje es muy corto o vacío, usar fallback
    if not mensaje or len(mensaje.strip()) < 2:
        return fallback

    # System prompt (identidad de prompts.yaml + capa editable de BD) + contexto temporal
    system_prompt = componer_system_prompt(config_db) + "\n\n" + construir_contexto_temporal()

    # Construir mensajes para la API
    mensajes = []
    for msg in historial:
        mensajes.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Agregar el mensaje actual
    mensajes.append({
        "role": "user",
        "content": mensaje
    })

    try:
        for _ in range(MAX_ITERACIONES_TOOLS):
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=system_prompt,
                tools=TOOLS_CLAUDE,
                messages=mensajes,
            )

            logger.info(f"Respuesta generada ({response.usage.input_tokens} in / {response.usage.output_tokens} out)")

            if response.stop_reason != "tool_use":
                bloques_texto = [bloque.text for bloque in response.content if bloque.type == "text"]
                return "\n".join(bloques_texto).strip() or fallback

            # Claude pidió usar una o más herramientas: ejecutarlas y devolver los resultados
            mensajes.append({"role": "assistant", "content": response.content})

            resultados_tools = []
            for bloque in response.content:
                if bloque.type == "tool_use":
                    resultado = await ejecutar_herramienta(bloque.name, bloque.input, telefono)
                    resultados_tools.append({
                        "type": "tool_result",
                        "tool_use_id": bloque.id,
                        "content": json.dumps(resultado, ensure_ascii=False),
                    })

            mensajes.append({"role": "user", "content": resultados_tools})

        logger.warning("Se alcanzó el límite de iteraciones de herramientas")
        return error_msg

    except Exception as e:
        logger.error(f"Error Claude API: {type(e).__name__}: {e} | causa: {type(e.__cause__).__name__}: {e.__cause__}")
        return error_msg

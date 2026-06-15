# agent/brain.py — Cerebro del agente: conexión con Claude API
# Generado por AgentKit

"""
Lógica de IA del agente. Lee el system prompt de prompts.yaml, le da acceso
a las herramientas de MDnails (búsqueda en knowledge y agendado de citas)
y genera respuestas usando la API de Anthropic Claude.
"""

import os
import json
import yaml
import logging
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from agent.tools import TOOLS_CLAUDE, ejecutar_herramienta

load_dotenv()
logger = logging.getLogger("agentkit")

# Cliente de Anthropic
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Límite de vueltas de uso de herramientas por mensaje (evita loops infinitos)
MAX_ITERACIONES_TOOLS = 5


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
    # Si el mensaje es muy corto o vacío, usar fallback
    if not mensaje or len(mensaje.strip()) < 2:
        return obtener_mensaje_fallback()

    system_prompt = cargar_system_prompt()

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
                return "\n".join(bloques_texto).strip() or obtener_mensaje_fallback()

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
        return obtener_mensaje_error()

    except Exception as e:
        logger.error(f"Error Claude API: {type(e).__name__}: {e} | causa: {type(e.__cause__).__name__}: {e.__cause__}")
        return obtener_mensaje_error()

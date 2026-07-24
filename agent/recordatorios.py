# agent/recordatorios.py — Recordatorios automáticos de citas por WhatsApp
# Generado por AgentKit

"""
Proceso en segundo plano: cada cierto tiempo busca las citas próximas (dentro de
las siguientes 24 h) que aún no se han recordado y le envía a la clienta un
recordatorio por WhatsApp, marcándolas para no repetir. Reduce los no-shows.
"""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from agent.memory import citas_por_recordar, marcar_recordatorio_enviado

logger = logging.getLogger("agentkit")

ZONA = ZoneInfo("America/Mexico_City")
INTERVALO_SEG = 1800  # revisa cada 30 minutos
HORAS_ANTES = 24      # recuerda citas dentro de las próximas 24 h


def _texto_recordatorio(cliente: str, servicio: str, inicia_en_iso: str) -> str:
    d = datetime.fromisoformat(inicia_en_iso).astimezone(ZONA)
    fecha = d.strftime("%d/%m")
    hora = d.strftime("%I:%M %p").lstrip("0")
    saludo = f" {cliente}" if cliente else ""
    return (
        f"Hola{saludo} 💅 Te recordamos tu cita en The Nail Society Spa: {servicio} "
        f"el {fecha} a las {hora}. Responde para confirmar, reagendar o cancelar. ¡Te esperamos!"
    )


async def _ciclo(proveedor):
    """Bucle principal: detecta y envía recordatorios cada INTERVALO_SEG."""
    while True:
        try:
            pendientes = await citas_por_recordar(horas_antes=HORAS_ANTES)
            for c in pendientes:
                if not c["telefono"]:
                    continue
                mensaje = _texto_recordatorio(c["cliente"], c["servicio"], c["inicia_en"])
                if await proveedor.enviar_mensaje(c["telefono"], mensaje):
                    await marcar_recordatorio_enviado(c["id"])
                    logger.info(f"Recordatorio enviado a {c['telefono']} (cita {c['id']})")
        except Exception as e:
            logger.error(f"Error en el ciclo de recordatorios: {e}")
        await asyncio.sleep(INTERVALO_SEG)


def iniciar_recordatorios(proveedor) -> asyncio.Task:
    """Arranca el proceso en segundo plano y devuelve la tarea (para cancelarla al cerrar)."""
    return asyncio.create_task(_ciclo(proveedor))

# agent/tools.py — Herramientas del agente
# Generado por AgentKit

"""
Herramientas específicas del negocio MDnails: búsqueda en la base de
conocimiento (FAQ) y registro de solicitudes de citas, respetando el
horario de atención del salón.
"""

import os
import uuid
import yaml
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from agent.memory import guardar_cita, buscar_o_crear_cliente, listar_servicios

logger = logging.getLogger("agentkit")

# Zona horaria del salón (Culiacán). Las citas se interpretan en hora local
# y se guardan como timestamp con zona horaria.
ZONA_HORARIA = ZoneInfo("America/Mazatlan")


def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def buscar_en_knowledge(consulta: str) -> str:
    """
    Busca información relevante en los archivos de /knowledge.
    Retorna el contenido más relevante encontrado.
    """
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                # Búsqueda simple por coincidencia de texto
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue

    if resultados:
        return "\n---\n".join(resultados)
    return "No encontré información específica sobre eso en mis archivos."


# ════════════════════════════════════════════════════════════
# AGENDAR CITAS — Horario de atención de MDnails
# 0=Lunes ... 5=Sábado, 6=Domingo (cerrado)
# Cada valor es (hora_apertura, hora_cierre) en formato 24h
# ════════════════════════════════════════════════════════════
HORARIO_SEMANA = {
    0: (9, 19),  # Lunes
    1: (9, 19),  # Martes
    2: (9, 19),  # Miércoles
    3: (9, 19),  # Jueves
    4: (9, 19),  # Viernes
    5: (9, 14),  # Sábado
    6: None,     # Domingo — cerrado
}


def verificar_disponibilidad(fecha: str, hora: str) -> dict:
    """Verifica si una fecha/hora cae dentro del horario de atención de MDnails."""
    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        hora_dt = datetime.strptime(hora, "%H:%M")
    except ValueError:
        return {
            "disponible": False,
            "mensaje": "Formato de fecha u hora inválido. Usa fecha=YYYY-MM-DD y hora=HH:MM (24 horas).",
        }

    horario_dia = HORARIO_SEMANA.get(fecha_dt.weekday())

    if horario_dia is None:
        return {"disponible": False, "mensaje": "Los domingos MDnails está cerrado."}

    apertura, cierre = horario_dia
    hora_decimal = hora_dt.hour + hora_dt.minute / 60

    if apertura <= hora_decimal < cierre:
        return {"disponible": True, "mensaje": "Horario disponible."}

    return {
        "disponible": False,
        "mensaje": f"Ese horario está fuera de atención. Ese día abrimos de {apertura}:00 a {cierre}:00.",
    }


async def agendar_cita(telefono: str, nombre_cliente: str, servicio: str, fecha: str, hora: str) -> dict:
    """Registra una solicitud de cita si la fecha/hora está dentro del horario de atención."""
    disponibilidad = verificar_disponibilidad(fecha, hora)
    if not disponibilidad["disponible"]:
        return {"exito": False, "mensaje": disponibilidad["mensaje"]}

    # Construir el inicio de la cita en la zona horaria del salón
    try:
        inicia_en = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M").replace(tzinfo=ZONA_HORARIA)
    except ValueError:
        return {"exito": False, "mensaje": "Formato de fecha u hora inválido. Usa YYYY-MM-DD y HH:MM."}

    # Resolver el servicio contra el catálogo de la DB.
    # Prioridad: 1) match exacto  2) el nombre más específico (más largo) que coincida,
    # para no confundir "Manicura" con "Manicura con gel".
    servicio_id = None
    duracion = 60
    objetivo = servicio.lower().strip()
    servicios = await listar_servicios()
    exacto = next((s for s in servicios if s["nombre"].lower() == objetivo), None)
    candidatos = [s for s in servicios if objetivo in s["nombre"].lower() or s["nombre"].lower() in objetivo]
    elegido = exacto or (max(candidatos, key=lambda s: len(s["nombre"])) if candidatos else None)
    if elegido:
        servicio_id = uuid.UUID(elegido["id"])
        duracion = elegido["duracion_min"]

    termina_en = inicia_en + timedelta(minutes=duracion)
    cliente_id = await buscar_o_crear_cliente(telefono, nombre_cliente)
    await guardar_cita(
        cliente_id=cliente_id,
        servicio_id=servicio_id,
        inicia_en=inicia_en,
        termina_en=termina_en,
        notas=f"Servicio solicitado por el cliente: {servicio}",
    )
    return {
        "exito": True,
        "mensaje": f"Cita registrada para {nombre_cliente}: {servicio} el {fecha} a las {hora}. MDnails la confirmará pronto.",
    }


# ════════════════════════════════════════════════════════════
# Definición de herramientas para Claude (tool use)
# ════════════════════════════════════════════════════════════
TOOLS_CLAUDE = [
    {
        "name": "listar_servicios",
        "description": "Devuelve el catálogo de servicios activos de MDnails (nombre, duración y precio). Úsala cuando el cliente pregunte qué servicios hay o cuánto duran/cuestan.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "buscar_en_knowledge",
        "description": "Busca información específica del negocio (servicios, ubicación, redes sociales, políticas, etc.) en los archivos de conocimiento de MDnails.",
        "input_schema": {
            "type": "object",
            "properties": {
                "consulta": {"type": "string", "description": "Palabra o frase clave a buscar"},
            },
            "required": ["consulta"],
        },
    },
    {
        "name": "verificar_disponibilidad",
        "description": "Verifica si una fecha y hora propuestas caen dentro del horario de atención de MDnails. Úsala antes de agendar una cita.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fecha": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
                "hora": {"type": "string", "description": "Hora en formato HH:MM (24 horas)"},
            },
            "required": ["fecha", "hora"],
        },
    },
    {
        "name": "agendar_cita",
        "description": "Registra una solicitud de cita para el cliente. Solo usar después de confirmar el servicio, fecha, hora y nombre del cliente, y de verificar la disponibilidad.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_cliente": {"type": "string", "description": "Nombre de la clienta o cliente"},
                "servicio": {"type": "string", "description": "Servicio solicitado (ej. Manicura con gel)"},
                "fecha": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
                "hora": {"type": "string", "description": "Hora en formato HH:MM (24 horas)"},
            },
            "required": ["nombre_cliente", "servicio", "fecha", "hora"],
        },
    },
]


async def ejecutar_herramienta(nombre: str, entrada: dict, telefono: str) -> dict:
    """Ejecuta la herramienta solicitada por Claude y retorna el resultado."""
    if nombre == "listar_servicios":
        return {"servicios": await listar_servicios()}

    if nombre == "buscar_en_knowledge":
        return {"resultado": buscar_en_knowledge(entrada.get("consulta", ""))}

    if nombre == "verificar_disponibilidad":
        return verificar_disponibilidad(entrada.get("fecha", ""), entrada.get("hora", ""))

    if nombre == "agendar_cita":
        return await agendar_cita(
            telefono=telefono,
            nombre_cliente=entrada.get("nombre_cliente", ""),
            servicio=entrada.get("servicio", ""),
            fecha=entrada.get("fecha", ""),
            hora=entrada.get("hora", ""),
        )

    return {"error": f"Herramienta desconocida: {nombre}"}

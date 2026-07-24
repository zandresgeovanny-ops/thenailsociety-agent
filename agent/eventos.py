# agent/eventos.py — Bus de eventos en tiempo real (LISTEN/NOTIFY → SSE)
# Generado por AgentKit

"""
Puente entre Postgres y el navegador para el panel en tiempo real.

Flujo:
  Postgres  --pg_notify('citas_cambio')-->  este listener (asyncpg)
     -->  se reparte a cada suscriptor (una cola por pestaña del panel abierta)
     -->  el endpoint SSE /panel/api/eventos lo envía al navegador.

Ventaja sobre Supabase Realtime: no expone la anon key ni exige políticas RLS
para el navegador; el panel mantiene su propia autenticación de FastAPI.

Degradación segura: si la base es SQLite (dev local) o el LISTEN falla, el bus
simplemente no emite y el panel sigue refrescando con su sondeo de respaldo (7s).
"""

import os
import re
import json
import asyncio
import logging

logger = logging.getLogger("agentkit")

CANAL = "citas_cambio"

# Suscriptores activos: cada pestaña del panel registra una cola.
_suscriptores: set[asyncio.Queue] = set()
_conexion = None  # conexión asyncpg dedicada al LISTEN


def _dsn_asyncpg() -> str | None:
    """Convierte DATABASE_URL al DSN que asyncpg.connect entiende (sin +asyncpg)."""
    url = os.getenv("DATABASE_URL", "")
    if "postgres" not in url:
        return None  # SQLite u otra: sin tiempo real
    # Normalizar esquema y quitar el driver de SQLAlchemy y la query libpq.
    url = re.sub(r"^postgresql\+asyncpg://", "postgresql://", url)
    url = re.sub(r"^postgres://", "postgresql://", url)
    url = url.split("?", 1)[0]
    return url


def publicar(payload: dict) -> None:
    """Reparte un evento a todos los suscriptores (no bloquea)."""
    muertos = []
    for cola in _suscriptores:
        try:
            cola.put_nowait(payload)
        except asyncio.QueueFull:
            muertos.append(cola)
    for cola in muertos:
        _suscriptores.discard(cola)


def _al_recibir(_conn, _pid, _canal, mensaje: str) -> None:
    """Callback de asyncpg cuando Postgres emite en el canal citas_cambio."""
    try:
        payload = json.loads(mensaje)
    except (ValueError, TypeError):
        payload = {"accion": "cambio"}
    publicar(payload)


async def iniciar_listener() -> None:
    """Abre la conexión dedicada y se suscribe al canal. Se llama en el arranque."""
    global _conexion
    dsn = _dsn_asyncpg()
    if not dsn:
        logger.info("Tiempo real desactivado (no hay Postgres); el panel usará sondeo.")
        return
    try:
        import asyncpg
        _conexion = await asyncpg.connect(dsn, ssl="require", statement_cache_size=0)
        await _conexion.add_listener(CANAL, _al_recibir)
        logger.info("Listener de tiempo real activo en el canal '%s'", CANAL)
    except Exception as e:  # noqa: BLE001 — cualquier fallo degrada a sondeo, no tumba el server
        logger.warning("No se pudo iniciar el listener de tiempo real: %s", e)
        _conexion = None


async def detener_listener() -> None:
    """Cierra la conexión del listener. Se llama al apagar el server."""
    global _conexion
    if _conexion is not None:
        try:
            await _conexion.remove_listener(CANAL, _al_recibir)
            await _conexion.close()
        except Exception:  # noqa: BLE001
            pass
        _conexion = None


async def suscribir():
    """Generador async de eventos para una conexión SSE. Uno por pestaña del panel."""
    cola: asyncio.Queue = asyncio.Queue(maxsize=100)
    _suscriptores.add(cola)
    try:
        while True:
            try:
                # Timeout para emitir un latido (keep-alive) y detectar desconexiones.
                evento = await asyncio.wait_for(cola.get(), timeout=25.0)
                yield evento
            except asyncio.TimeoutError:
                yield {"accion": "ping"}
    finally:
        _suscriptores.discard(cola)

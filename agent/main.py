# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit

"""
Servidor principal del agente de WhatsApp.
Funciona con cualquier proveedor (Meta, Twilio) gracias a la capa de providers.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial
from agent.providers import obtener_proveedor
from agent.panel import router as panel_router
from agent.reservas import router as reservas_router
from agent.auth import router as auth_router
from agent.recordatorios import iniciar_recordatorios

load_dotenv()

# Configuración de logging según entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

# Proveedor de WhatsApp (se configura en .env con WHATSAPP_PROVIDER)
proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
    await inicializar_db()
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor AgentKit corriendo en puerto {PORT}")
    logger.info(f"Proveedor de WhatsApp: {proveedor.__class__.__name__}")
    # Recordatorios automáticos de citas en segundo plano
    tarea_recordatorios = iniciar_recordatorios(proveedor)
    logger.info("Recordatorios automáticos activados")
    yield
    tarea_recordatorios.cancel()


app = FastAPI(
    title="AgentKit — WhatsApp AI Agent",
    version="1.0.0",
    lifespan=lifespan
)

# Archivos estáticos (JS externalizado para poder usar una CSP estricta)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Panel de administración de citas (dashboard web protegido con contraseña)
app.include_router(panel_router)

# Portal público de reservas para clientas
app.include_router(reservas_router)

# Login / logout y autenticación por roles
app.include_router(auth_router)


@app.middleware("http")
async def cabeceras_seguridad(request: Request, call_next):
    """Cabeceras de seguridad básicas (anti-clickjacking, anti-sniffing)."""
    respuesta = await call_next(request)
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "DENY"
    respuesta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Content-Security-Policy: limita de dónde se cargan recursos para reducir
    # el impacto de un XSS. Las páginas públicas (login y portal de reservas) ya
    # tienen su JS externalizado, así que usan una política ESTRICTA sin
    # 'unsafe-inline' en scripts. El panel (tras login) aún usa scripts inline,
    # por eso conserva 'unsafe-inline'. Los estilos inline se permiten en ambas.
    ruta = request.url.path
    pagina_estricta = ruta == "/login" or ruta == "/reservar" or ruta.startswith("/reservar/")
    script_src = "script-src 'self'" if pagina_estricta else "script-src 'self' 'unsafe-inline'"
    respuesta.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        f"{script_src}; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    return respuesta


@app.get("/")
async def health_check():
    """Endpoint de salud para Railway/monitoreo."""
    return {"status": "ok", "service": "agentkit"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    """Verificación GET del webhook (requerido por Meta Cloud API, no-op para otros)."""
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recibe mensajes de WhatsApp via el proveedor configurado.
    Procesa el mensaje, genera respuesta con Claude y la envía de vuelta.
    """
    try:
        # Parsear webhook — el proveedor normaliza el formato
        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            # Ignorar mensajes propios o vacíos
            if msg.es_propio or not msg.texto:
                continue

            logger.info(f"Mensaje de {msg.telefono}: {msg.texto}")

            # Obtener historial ANTES de guardar el mensaje actual
            # (brain.py agrega el mensaje actual, evitando duplicados)
            historial = await obtener_historial(msg.telefono)

            # Generar respuesta con Claude
            respuesta = await generar_respuesta(msg.texto, historial, msg.telefono)

            # Guardar mensaje del usuario Y respuesta del agente en memoria
            await guardar_mensaje(msg.telefono, "user", msg.texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)

            # Enviar respuesta por WhatsApp via el proveedor
            await proveedor.enviar_mensaje(msg.telefono, respuesta)

            logger.info(f"Respuesta a {msg.telefono}: {respuesta}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail="Error interno")

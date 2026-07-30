# agent/reservas.py — Portal de reservas para clientas (Client_Portal)
# Generado por AgentKit

"""
Página pública donde la clienta agenda su cita paso a paso:
servicio → empleada (opcional) → fecha y hora → confirmación.

La disponibilidad se calcula en el servidor (memory.slots_disponibles) respetando
duración del servicio, horario de la empleada y citas ya ocupadas. El no-solapamiento
final lo garantiza un constraint en la base de datos.
"""

import uuid
import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import IntegrityError

from agent.seguridad import limitar

from agent.memory import (
    ZONA_SALON, catalogo_servicios, listar_empleados, slots_disponibles,
    buscar_o_crear_cliente, guardar_cita, listar_sucursales, slots_sucursal,
)
from agent.branding import aplicar_marca

logger = logging.getLogger("agentkit")
router = APIRouter(prefix="/reservar")

# Días y meses en español, para redactar la confirmación sin depender del
# locale del servidor (en Railway el contenedor viene en inglés).
_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")

# Lada por defecto para números escritos sin país. El salón es de
# Aguascalientes, así que un número local de 10 dígitos es mexicano.
LADA_POR_DEFECTO = "+52"


def _normalizar_telefono(crudo: str) -> str | None:
    """
    Deja el teléfono en formato E.164 (+52XXXXXXXXXX), que es lo que exige
    WhatsApp. La clienta escribe como quiere: "449 273 3769", "(449) 273-3769"
    o "+52 449 273 3769". Devuelve None si no parece un número válido.
    """
    digitos = "".join(c for c in crudo if c.isdigit())
    if crudo.strip().startswith("+"):
        return f"+{digitos}" if len(digitos) >= 11 else None
    if len(digitos) == 10:  # número local
        return f"{LADA_POR_DEFECTO}{digitos}"
    if len(digitos) == 12 and digitos.startswith("52"):
        return f"+{digitos}"
    return None


def _texto_confirmacion(nombre: str, servicio: str, cuando: datetime,
                        sucursal: str | None) -> str:
    """Mensaje de confirmación, con la voz de la marca."""
    dia = _DIAS[cuando.weekday()]
    fecha = f"{dia} {cuando.day} de {_MESES[cuando.month - 1]}"
    hora = cuando.strftime("%H:%M")
    donde = f"\nSucursal {sucursal}." if sucursal else ""
    return (
        f"¡Hola {nombre}! Tu cita en The Nail Society quedó confirmada. ✨\n\n"
        f"{servicio}\n"
        f"{fecha} a las {hora}.{donde}\n\n"
        f"Si necesitas moverla o cancelarla, respóndeme por aquí y lo vemos.\n"
        f"Te esperamos. 🤍"
    )


async def _enviar_confirmacion(telefono: str, mensaje: str) -> None:
    """
    Manda la confirmación por WhatsApp.

    Va aislado a propósito: si Twilio falla o el número no es válido, la cita
    YA está guardada y la clienta ya vio su confirmación en pantalla. Un fallo
    de mensajería nunca debe tumbar una reserva.
    """
    try:
        from agent.providers import obtener_proveedor

        proveedor = obtener_proveedor()
        if await proveedor.enviar_mensaje(telefono, mensaje):
            logger.info(f"Confirmación enviada a {telefono}")
        else:
            logger.warning(f"No se pudo enviar la confirmación a {telefono}")
    except Exception as e:
        logger.error(f"Error enviando la confirmación de reserva: {e}")


@router.get("/api/servicios")
async def api_servicios():
    return await catalogo_servicios()


@router.get("/api/empleados")
async def api_empleados():
    return await listar_empleados()


@router.get("/api/sucursales")
async def api_sucursales():
    return await listar_sucursales()


@router.get("/api/disponibilidad")
async def api_disponibilidad(
    servicio_id: str,
    fecha: str,
    empleado_id: str | None = None,
    sucursal_id: str | None = None,
):
    # Si se elige una especialista concreta, su agenda manda. Si sólo se elige
    # sucursal, se unen los huecos de todas sus especialistas.
    if empleado_id:
        slots = await slots_disponibles(servicio_id, empleado_id, fecha)
    elif sucursal_id:
        slots = await slots_sucursal(servicio_id, sucursal_id, fecha)
    else:
        slots = await slots_disponibles(servicio_id, None, fecha)
    return {"slots": slots}


@router.post("/api/reservar")
async def api_reservar(payload: dict, request: Request):
    limitar(request, "reserva", maximo=6, ventana_seg=600)  # anti-spam de reservas públicas
    nombre = (payload.get("nombre") or "").strip()
    telefono = (payload.get("telefono") or "").strip()
    servicio_id = payload.get("servicio_id")
    empleado_id = payload.get("empleado_id") or None
    sucursal_id = payload.get("sucursal_id") or None
    fecha = payload.get("fecha")
    hora = payload.get("hora")

    if not all([nombre, telefono, servicio_id, fecha, hora]):
        raise HTTPException(status_code=400, detail="Faltan datos para la reserva")

    # Duración del servicio (para calcular el fin de la cita)
    servicios = await catalogo_servicios()
    servicio = next((s for s in servicios if s["id"] == servicio_id), None)
    if servicio is None:
        raise HTTPException(status_code=400, detail="Servicio inválido")

    try:
        inicia_en = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M").replace(tzinfo=ZONA_SALON)
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha u hora inválida")
    termina_en = inicia_en + timedelta(minutes=servicio["duracion_min"])

    # ── La sucursal no puede quedar vacía ────────────────────────────────
    # Una cita sin sede es inservible para el salón: no saben dónde atenderla.
    # Se resuelve en dos niveles para que ningún cliente (web, portal o un
    # POST directo) pueda colarla:
    #   1. Si viene especialista pero no sucursal, se deduce de ella.
    #   2. Si sigue sin sucursal, se rechaza la reserva.
    if empleado_id and not sucursal_id:
        equipo = await listar_empleados()
        sucursal_id = next(
            (e["sucursal_id"] for e in equipo if str(e["id"]) == str(empleado_id)), None
        )

    if not sucursal_id:
        raise HTTPException(
            status_code=400,
            detail="Elige una sucursal para poder agendar tu cita.",
        )

    cliente_id = await buscar_o_crear_cliente(telefono, nombre)
    try:
        await guardar_cita(
            cliente_id=cliente_id,
            servicio_id=uuid.UUID(servicio_id),
            inicia_en=inicia_en,
            termina_en=termina_en,
            empleado_id=uuid.UUID(empleado_id) if empleado_id else None,
            sucursal_id=uuid.UUID(sucursal_id) if sucursal_id else None,
            notas=f"Reserva web · {servicio['nombre']}",
            origen="web",
        )
    except IntegrityError:
        # El constraint de no-solapamiento rechazó la cita (alguien tomó el turno)
        raise HTTPException(status_code=409, detail="Ese horario acaba de ocuparse, elige otro.")

    # ── Confirmación por WhatsApp ────────────────────────────────────────
    # Se manda en segundo plano: la clienta no debe esperar a que Twilio
    # responda para ver su confirmación en pantalla.
    telefono_e164 = _normalizar_telefono(telefono)
    if telefono_e164:
        nombre_sucursal = None
        if sucursal_id:
            sucursales = await listar_sucursales()
            nombre_sucursal = next(
                (s["nombre"] for s in sucursales if str(s["id"]) == str(sucursal_id)), None
            )
        asyncio.create_task(
            _enviar_confirmacion(
                telefono_e164,
                _texto_confirmacion(nombre, servicio["nombre"], inicia_en, nombre_sucursal),
            )
        )
    else:
        logger.warning(f"Teléfono no reconocido, sin confirmación: {telefono!r}")

    return {"ok": True, "mensaje": f"¡Listo {nombre}! Tu cita de {servicio['nombre']} quedó registrada."}


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def pagina_reservar():
    return aplicar_marca(_PAGINA_HTML)


_PAGINA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Nail Society Spa · Reservar cita</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,400;1,600&display=swap" rel="stylesheet">
<style>
  /* Paleta de The Nail Society: marfil, dorado y negro. Antes esto venía del
     proyecto anterior (MD Nails) en morado y magenta — nada que ver.
     Los nombres --rosa* se conservan para no reescribir toda la hoja; hoy
     apuntan al dorado de marca. El dorado nunca es color de texto: para eso
     está --rosa-2, que es el bronce y sí pasa contraste AA. */
  :root{--rosa:#c9a24d;--rosa-2:#7a5f22;--rosa-suave:#f7f0df;--tinta:#1a1a1a;
    --gris:#6b6560;--panel:#ffffff;--linea:#e6ded1;--ok:#1f9d6b;--bg:#f7f4ee;
    --oro:#c9a24d;--oro-claro:#e0bd6f;--acento-sobre:#171310;
    --serif:'Cormorant Garamond',Georgia,serif;
    --sombra:0 10px 30px rgba(20,16,10,.10)}
  *{box-sizing:border-box}
  body{margin:0;font-family:'Inter',system-ui,sans-serif;color:var(--tinta);
    background:
      radial-gradient(820px 440px at 100% -10%, rgba(201,162,77,.16), transparent 55%),
      radial-gradient(700px 400px at -10% 10%, rgba(201,162,77,.10), transparent 52%),
      var(--bg);min-height:100vh}
  /* Trama de damasco, el mismo recurso que el hero y las reseñas de la web */
  body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.4;
    background-image:radial-gradient(rgba(201,162,77,.22) 1px,transparent 1px),
                     radial-gradient(rgba(201,162,77,.13) 1px,transparent 1px);
    background-size:26px 26px,26px 26px;background-position:0 0,13px 13px}
  .wrap{position:relative;z-index:1}
  .head h1{font-family:var(--serif)}
  .wrap{max-width:560px;margin:0 auto;padding:20px 16px 40px}
  .head{text-align:center;margin:14px 0 22px}
  .logo{width:88px;height:88px;border-radius:50%;display:inline-block;box-shadow:0 0 0 1px var(--linea),0 12px 32px rgba(201,162,77,.28);animation:pop .5s ease both}
  .head h1{font-family:var(--serif);font-size:24px;margin:12px 0 2px}
  .head p{color:var(--gris);margin:0;font-size:14px}
  /* Pasos */
  .pasos{display:flex;justify-content:center;gap:8px;margin:18px 0 24px}
  .paso{width:30px;height:5px;border-radius:99px;background:var(--linea);transition:.3s}
  .paso.on{background:linear-gradient(90deg,var(--rosa),var(--rosa-2))}
  .panel{background:var(--panel);border:1px solid var(--linea);border-radius:20px;box-shadow:var(--sombra);padding:20px;animation:rise .35s ease both}
  .panel h2{font-family:var(--serif);font-size:19px;margin:0 0 4px}
  .panel .sub{color:var(--gris);font-size:13.5px;margin:0 0 16px}
  /* Tarjetas seleccionables */
  .opt{border:1.5px solid var(--linea);border-radius:14px;padding:14px 16px;margin-bottom:10px;cursor:pointer;display:flex;align-items:center;gap:12px;transition:.15s;background:#ffffff}
  .opt:hover{border-color:var(--rosa);transform:translateY(-1px)}
  .opt.sel{border-color:var(--rosa);background:var(--rosa-suave);box-shadow:0 4px 16px rgba(201,162,77,.22)}
  .opt .info{flex:1}
  .opt .n{font-weight:600}
  .opt .meta{font-size:12.5px;color:var(--gris);margin-top:2px}
  .opt .precio{font-weight:700;color:var(--rosa)}
  .avatar{width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,#c9a24d,#a67c2e);display:grid;place-items:center;color:#fff;font-weight:700}
  .cat{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--rosa);font-weight:700;margin:14px 0 8px}
  /* Fecha y slots */
  input[type=date],input[type=text],input[type=tel]{width:100%;padding:12px 13px;border:1.5px solid var(--linea);border-radius:12px;font-family:inherit;font-size:15px;margin-bottom:12px;background:#f7f4ee;color:var(--tinta)}
  input::placeholder{color:#6b6560}
  input:focus{outline:none;border-color:var(--rosa)}
  label{font-size:13px;font-weight:600;color:var(--gris);display:block;margin-bottom:6px}
  .slots{display:grid;grid-template-columns:repeat(auto-fill,minmax(78px,1fr));gap:9px;margin-top:6px}
  .slot{border:1.5px solid var(--linea);border-radius:11px;padding:11px 6px;text-align:center;cursor:pointer;font-weight:600;font-size:14px;background:#ffffff;transition:.12s}
  .slot:hover{border-color:var(--rosa)}
  .slot.sel{background:linear-gradient(135deg,var(--rosa),var(--rosa-2));color:#fff;border-color:transparent}
  .aviso{color:var(--gris);font-size:13.5px;text-align:center;padding:18px}
  /* Botones */
  .nav{display:flex;gap:10px;margin-top:18px}
  .btn{flex:1;border:none;border-radius:13px;padding:13px;font-weight:700;font-size:15px;cursor:pointer;font-family:inherit;transition:.15s}
  .btn.primary{background:linear-gradient(135deg,var(--rosa),var(--rosa-2));color:#fff;box-shadow:0 8px 20px rgba(201,162,77,.38)}
  .btn.primary:disabled{opacity:.45;cursor:not-allowed;box-shadow:none}
  .btn.ghost{background:#f4efe6;color:var(--tinta);flex:0 0 auto;padding:13px 18px}
  /* Resumen / éxito */
  .resumen{background:var(--rosa-suave);border-radius:14px;padding:16px;margin-bottom:8px;font-size:14px;line-height:1.7}
  .resumen b{color:var(--rosa)}
  .exito{text-align:center;padding:14px}
  .exito .check{width:70px;height:70px;border-radius:50%;background:var(--ok);color:#e8f5ef;font-size:38px;display:inline-grid;place-items:center;animation:pop .4s ease both}
  .exito h2{margin:16px 0 6px}
  .skel{height:42px;border-radius:11px;background:linear-gradient(90deg,#faf7f1 25%,#e6ded1 37%,#faf7f1 63%);background-size:400% 100%;animation:shimmer 1.4s infinite}
  /* Pie */
  .pie{margin-top:26px;text-align:center;color:var(--gris);font-size:12.5px;line-height:1.7}
  .pie .red{display:inline-flex;gap:16px;justify-content:center;margin-top:8px}
  .pie a{color:var(--rosa);text-decoration:none;font-weight:600}
  @keyframes pop{from{opacity:0;transform:scale(.6)}to{opacity:1;transform:none}}
  @keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
  @keyframes shimmer{0%{background-position:100% 0}100%{background-position:-100% 0}}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <img class="logo" src="__LOGO__" alt="The Nail Society Spa">
    <h1>The Nail Society Spa</h1>
    <p>Reserva tu cita en segundos</p>
  </div>
  <!-- 5 pasos: servicio · sucursal · especialista · fecha y hora · datos -->
  <div class="pasos">
    <div class="paso on" data-p="1"></div><div class="paso" data-p="2"></div>
    <div class="paso" data-p="3"></div><div class="paso" data-p="4"></div>
    <div class="paso" data-p="5"></div>
  </div>
  <div id="contenido"></div>
  <div class="pie">
    Sucursal Sur: Av. Aguascalientes Sur #117, Villa Jardín II · Sucursal Norte: Blvd. Luis Donaldo Colosio 400 · Aguascalientes
    <div class="red">
      <a href="https://instagram.com/thenailsociety_ags" target="_blank" rel="noopener">@thenailsociety_ags</a>
      <a href="https://wa.me/524492733769" target="_blank" rel="noopener">WhatsApp</a>
    </div>
  </div>
</div>

<script src="/static/reservar.js"></script>
</body>
</html>
"""

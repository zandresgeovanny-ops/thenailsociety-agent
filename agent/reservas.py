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
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import IntegrityError

from agent.memory import (
    ZONA_SALON, catalogo_servicios, listar_empleados, slots_disponibles,
    buscar_o_crear_cliente, guardar_cita,
)
from agent.branding import LOGO_DATA_URI

logger = logging.getLogger("agentkit")
router = APIRouter(prefix="/reservar")


@router.get("/api/servicios")
async def api_servicios():
    return await catalogo_servicios()


@router.get("/api/empleados")
async def api_empleados():
    return await listar_empleados()


@router.get("/api/disponibilidad")
async def api_disponibilidad(servicio_id: str, fecha: str, empleado_id: str | None = None):
    return {"slots": await slots_disponibles(servicio_id, empleado_id, fecha)}


@router.post("/api/reservar")
async def api_reservar(payload: dict):
    nombre = (payload.get("nombre") or "").strip()
    telefono = (payload.get("telefono") or "").strip()
    servicio_id = payload.get("servicio_id")
    empleado_id = payload.get("empleado_id") or None
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

    cliente_id = await buscar_o_crear_cliente(telefono, nombre)
    try:
        await guardar_cita(
            cliente_id=cliente_id,
            servicio_id=uuid.UUID(servicio_id),
            inicia_en=inicia_en,
            termina_en=termina_en,
            empleado_id=uuid.UUID(empleado_id) if empleado_id else None,
            notas=f"Reserva web · {servicio['nombre']}",
            origen="web",
        )
    except IntegrityError:
        # El constraint de no-solapamiento rechazó la cita (alguien tomó el turno)
        raise HTTPException(status_code=409, detail="Ese horario acaba de ocuparse, elige otro.")

    return {"ok": True, "mensaje": f"¡Listo {nombre}! Tu cita de {servicio['nombre']} quedó registrada."}


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def pagina_reservar():
    return _PAGINA_HTML.replace("__LOGO__", LOGO_DATA_URI)


_PAGINA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MDnails · Reservar cita</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
<style>
  :root{--rosa:#e8308f;--rosa-2:#c41f73;--rosa-suave:#2a1830;--tinta:#f1ebf5;--gris:#9d92aa;--panel:#221c2b;--linea:#352c40;--ok:#2ecb8f;--bg:#141019;--sombra:0 10px 30px rgba(0,0,0,.45)}
  *{box-sizing:border-box}
  body{margin:0;font-family:'Inter',system-ui,sans-serif;color:var(--tinta);
    background:radial-gradient(820px 440px at 100% -10%, rgba(232,48,143,.20), transparent 55%), var(--bg);min-height:100vh}
  .wrap{max-width:560px;margin:0 auto;padding:20px 16px 40px}
  .head{text-align:center;margin:14px 0 22px}
  .logo{width:88px;height:88px;border-radius:50%;display:inline-block;box-shadow:0 0 0 1px var(--linea),0 12px 32px rgba(232,48,143,.28);animation:pop .5s ease both}
  .head h1{font-family:'Playfair Display',serif;font-size:24px;margin:12px 0 2px}
  .head p{color:var(--gris);margin:0;font-size:14px}
  /* Pasos */
  .pasos{display:flex;justify-content:center;gap:8px;margin:18px 0 24px}
  .paso{width:30px;height:5px;border-radius:99px;background:var(--linea);transition:.3s}
  .paso.on{background:linear-gradient(90deg,var(--rosa),var(--rosa-2))}
  .panel{background:var(--panel);border:1px solid var(--linea);border-radius:20px;box-shadow:var(--sombra);padding:20px;animation:rise .35s ease both}
  .panel h2{font-family:'Playfair Display',serif;font-size:19px;margin:0 0 4px}
  .panel .sub{color:var(--gris);font-size:13.5px;margin:0 0 16px}
  /* Tarjetas seleccionables */
  .opt{border:1.5px solid var(--linea);border-radius:14px;padding:14px 16px;margin-bottom:10px;cursor:pointer;display:flex;align-items:center;gap:12px;transition:.15s;background:#1d1825}
  .opt:hover{border-color:var(--rosa);transform:translateY(-1px)}
  .opt.sel{border-color:var(--rosa);background:var(--rosa-suave);box-shadow:0 4px 16px rgba(232,48,143,.22)}
  .opt .info{flex:1}
  .opt .n{font-weight:600}
  .opt .meta{font-size:12.5px;color:var(--gris);margin-top:2px}
  .opt .precio{font-weight:700;color:var(--rosa)}
  .avatar{width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,#e8308f,#7d1a52);display:grid;place-items:center;color:#fff;font-weight:700}
  .cat{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--rosa);font-weight:700;margin:14px 0 8px}
  /* Fecha y slots */
  input[type=date],input[type=text],input[type=tel]{width:100%;padding:12px 13px;border:1.5px solid var(--linea);border-radius:12px;font-family:inherit;font-size:15px;margin-bottom:12px;background:#1b1622;color:var(--tinta)}
  input::placeholder{color:#6f6580}
  input:focus{outline:none;border-color:var(--rosa)}
  label{font-size:13px;font-weight:600;color:var(--gris);display:block;margin-bottom:6px}
  .slots{display:grid;grid-template-columns:repeat(auto-fill,minmax(78px,1fr));gap:9px;margin-top:6px}
  .slot{border:1.5px solid var(--linea);border-radius:11px;padding:11px 6px;text-align:center;cursor:pointer;font-weight:600;font-size:14px;background:#1d1825;transition:.12s}
  .slot:hover{border-color:var(--rosa)}
  .slot.sel{background:linear-gradient(135deg,var(--rosa),var(--rosa-2));color:#fff;border-color:transparent}
  .aviso{color:var(--gris);font-size:13.5px;text-align:center;padding:18px}
  /* Botones */
  .nav{display:flex;gap:10px;margin-top:18px}
  .btn{flex:1;border:none;border-radius:13px;padding:13px;font-weight:700;font-size:15px;cursor:pointer;font-family:inherit;transition:.15s}
  .btn.primary{background:linear-gradient(135deg,var(--rosa),var(--rosa-2));color:#fff;box-shadow:0 8px 20px rgba(232,48,143,.38)}
  .btn.primary:disabled{opacity:.45;cursor:not-allowed;box-shadow:none}
  .btn.ghost{background:#2a2433;color:var(--tinta);flex:0 0 auto;padding:13px 18px}
  /* Resumen / éxito */
  .resumen{background:var(--rosa-suave);border-radius:14px;padding:16px;margin-bottom:8px;font-size:14px;line-height:1.7}
  .resumen b{color:var(--rosa)}
  .exito{text-align:center;padding:14px}
  .exito .check{width:70px;height:70px;border-radius:50%;background:var(--ok);color:#0c2a1f;font-size:38px;display:inline-grid;place-items:center;animation:pop .4s ease both}
  .exito h2{margin:16px 0 6px}
  .skel{height:42px;border-radius:11px;background:linear-gradient(90deg,#241f2e 25%,#2e2738 37%,#241f2e 63%);background-size:400% 100%;animation:shimmer 1.4s infinite}
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
    <img class="logo" src="__LOGO__" alt="MD nails">
    <h1>MD nails</h1>
    <p>Reserva tu cita en segundos</p>
  </div>
  <div class="pasos">
    <div class="paso on" data-p="1"></div><div class="paso" data-p="2"></div>
    <div class="paso" data-p="3"></div><div class="paso" data-p="4"></div>
  </div>
  <div id="contenido"></div>
  <div class="pie">
    Blvd Benjamín Hill #3960 local 1, col Pemex · Culiacán, Sin.
    <div class="red">
      <a href="https://instagram.com/mdnailscln" target="_blank" rel="noopener">@mdnailscln</a>
      <a href="https://wa.me/5216674281696" target="_blank" rel="noopener">WhatsApp</a>
    </div>
  </div>
</div>

<script>
const API = "/reservar/api";
const TZ = "America/Mazatlan";
let paso = 1;
let servicios = [], empleados = [];
const sel = { servicio:null, empleado:null, empleadoNombre:"Cualquiera disponible", fecha:null, hora:null };

async function api(p, opts){ const r = await fetch(API+p, opts); if(!r.ok){ const e=await r.json().catch(()=>({})); throw new Error(e.detail||("HTTP "+r.status)); } return r.json(); }
function ampm(hhmm){ if(!hhmm) return ""; const [H,M]=hhmm.split(":").map(Number); const d=new Date(); d.setHours(H,M,0,0); return d.toLocaleTimeString("es-MX",{hour:"numeric",minute:"2-digit",hour12:true}); }
function marcarPasos(){ document.querySelectorAll(".paso").forEach(p=>p.classList.toggle("on", +p.dataset.p <= paso)); }
function hoyISO(){ return new Date().toLocaleDateString("en-CA",{timeZone:TZ}); }  // YYYY-MM-DD

// ---------- Paso 1: servicio ----------
async function pintarServicios(){
  paso=1; marcarPasos();
  const c = document.getElementById("contenido");
  c.innerHTML = `<div class="panel"><h2>Elige tu servicio</h2><p class="sub">¿Qué te quieres hacer hoy?</p><div id="lista"></div></div>`;
  if(!servicios.length) servicios = await api("/servicios");
  const cats = [...new Set(servicios.map(s=>s.categoria))];
  let html = "";
  for(const cat of cats){
    html += `<div class="cat">${cat}</div>`;
    for(const s of servicios.filter(x=>x.categoria===cat)){
      const precio = s.precio!=null ? `$${s.precio}` : "";
      html += `<div class="opt ${sel.servicio===s.id?'sel':''}" onclick="elegirServicio('${s.id}')">
        <div class="info"><div class="n">${s.nombre}</div><div class="meta">${s.duracion_min} min</div></div>
        <div class="precio">${precio}</div></div>`;
    }
  }
  document.getElementById("lista").innerHTML = html;
}
function elegirServicio(id){ sel.servicio=id; sel.hora=null; pintarEmpleados(); }

// ---------- Paso 2: empleada ----------
async function pintarEmpleados(){
  paso=2; marcarPasos();
  const c = document.getElementById("contenido");
  c.innerHTML = `<div class="panel"><h2>Elige tu manicurista</h2><p class="sub">Opcional — puedes dejar que el salón asigne.</p><div id="lista"></div>
    <div class="nav"><button class="btn ghost" onclick="pintarServicios()">Atrás</button></div></div>`;
  if(!empleados.length) empleados = await api("/empleados");
  let html = `<div class="opt ${sel.empleado===null?'sel':''}" onclick="elegirEmpleado(null,'Cualquiera disponible')">
      <div class="avatar">✨</div><div class="info"><div class="n">Cualquiera disponible</div><div class="meta">El salón asigna</div></div></div>`;
  for(const e of empleados){
    html += `<div class="opt ${sel.empleado===e.id?'sel':''}" onclick="elegirEmpleado('${e.id}','${e.nombre}')">
      <div class="avatar">${e.nombre[0]}</div><div class="info"><div class="n">${e.nombre}</div></div></div>`;
  }
  document.getElementById("lista").innerHTML = html;
}
function elegirEmpleado(id,nombre){ sel.empleado=id; sel.empleadoNombre=nombre; sel.hora=null; pintarFecha(); }

// ---------- Paso 3: fecha y hora ----------
function pintarFecha(){
  paso=3; marcarPasos();
  const c = document.getElementById("contenido");
  c.innerHTML = `<div class="panel"><h2>Fecha y hora</h2><p class="sub">Elige el día y un horario disponible.</p>
    <label>Día</label><input type="date" id="fecha" min="${hoyISO()}" value="${sel.fecha||hoyISO()}" onchange="cargarSlots()">
    <label>Horarios disponibles</label><div id="slots"></div>
    <div class="nav"><button class="btn ghost" onclick="pintarEmpleados()">Atrás</button></div></div>`;
  sel.fecha = document.getElementById("fecha").value;
  cargarSlots();
}
async function cargarSlots(){
  sel.fecha = document.getElementById("fecha").value; sel.hora=null;
  const cont = document.getElementById("slots");
  cont.className=""; cont.innerHTML = `<div class="slots">${'<div class="skel"></div>'.repeat(6)}</div>`;
  try{
    const q = new URLSearchParams({servicio_id:sel.servicio, fecha:sel.fecha});
    if(sel.empleado) q.set("empleado_id", sel.empleado);
    const {slots} = await api("/disponibilidad?"+q.toString());
    if(!slots.length){ cont.innerHTML = `<div class="aviso">No hay horarios libres ese día 😕<br>Prueba con otra fecha.</div>`; return; }
    cont.innerHTML = `<div class="slots">${slots.map(h=>`<div class="slot" onclick="elegirHora('${h}',this)">${ampm(h)}</div>`).join("")}</div>`;
  }catch(e){ cont.innerHTML = `<div class="aviso">No se pudo cargar la disponibilidad.</div>`; }
}
function elegirHora(h, el){
  sel.hora=h;
  document.querySelectorAll(".slot").forEach(s=>s.classList.remove("sel"));
  el.classList.add("sel");
  setTimeout(pintarConfirmacion, 180);
}

// ---------- Paso 4: datos y confirmar ----------
function pintarConfirmacion(){
  paso=4; marcarPasos();
  const s = servicios.find(x=>x.id===sel.servicio);
  const f = new Date(sel.fecha+"T12:00:00").toLocaleDateString("es-MX",{weekday:"long",day:"numeric",month:"long"});
  const c = document.getElementById("contenido");
  c.innerHTML = `<div class="panel"><h2>Confirma tu cita</h2><p class="sub">Solo faltan tus datos.</p>
    <div class="resumen">💅 <b>${s.nombre}</b> (${s.duracion_min} min)<br>👩 ${sel.empleadoNombre}<br>📅 ${f}<br>🕒 ${ampm(sel.hora)}</div>
    <label>Tu nombre</label><input type="text" id="nombre" placeholder="Ej. Mariana López">
    <label>Tu WhatsApp</label><input type="tel" id="telefono" placeholder="Ej. 6671234567">
    <div class="nav">
      <button class="btn ghost" onclick="pintarFecha()">Atrás</button>
      <button class="btn primary" id="btnOk" onclick="confirmar()">Confirmar cita</button>
    </div></div>`;
}
async function confirmar(){
  const nombre = document.getElementById("nombre").value.trim();
  const telefono = document.getElementById("telefono").value.trim();
  if(!nombre || !telefono){ alert("Escribe tu nombre y WhatsApp 🙏"); return; }
  const btn = document.getElementById("btnOk"); btn.disabled=true; btn.textContent="Reservando...";
  try{
    await api("/reservar",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({nombre,telefono,servicio_id:sel.servicio,empleado_id:sel.empleado,fecha:sel.fecha,hora:sel.hora})});
    pintarExito(nombre);
  }catch(e){ btn.disabled=false; btn.textContent="Confirmar cita"; alert(e.message); cargarSlots && null; }
}
function pintarExito(nombre){
  const s = servicios.find(x=>x.id===sel.servicio);
  const f = new Date(sel.fecha+"T12:00:00").toLocaleDateString("es-MX",{weekday:"long",day:"numeric",month:"long"});
  document.getElementById("contenido").innerHTML = `<div class="panel exito">
    <div class="check">✓</div><h2>¡Cita reservada!</h2>
    <p class="sub">Gracias ${nombre}, te esperamos.<br><b>${s.nombre}</b> · ${f} · ${ampm(sel.hora)}</p>
    <div class="nav"><button class="btn primary" onclick="location.reload()">Reservar otra</button></div></div>`;
}

pintarServicios();
</script>
</body>
</html>
"""

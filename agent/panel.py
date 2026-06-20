# agent/panel.py — Panel de administración (citas y empleadas)
# Generado por AgentKit

"""
Dashboard interno del salón, servido por el backend (FastAPI) y protegido con
sesión por roles. El admin gestiona citas y empleadas; la empleada solo ve su
agenda. Los datos se leen del lado del servidor (no se exponen públicamente).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from agent.memory import (
    listar_citas, listar_empleados, crear_empleado, actualizar_cita,
    desactivar_empleado, establecer_horario_empleado, gestionar_empleados,
    eliminar_empleado,
)
from agent.auth import usuario_actual, requiere_panel

logger = logging.getLogger("agentkit")

router = APIRouter(prefix="/panel")

ESTADOS_VALIDOS = {"pendiente", "confirmada", "cancelada", "completada"}


def _solo_admin(user: dict):
    if user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Solo el administrador puede hacer esto")


# ════════════════════════════════════════════════════════════
# API JSON
# ════════════════════════════════════════════════════════════
@router.get("/api/yo")
async def api_yo(user: dict = Depends(requiere_panel)):
    return {"nombre": user["nombre"], "rol": user["rol"], "empleado_id": user["empleado_id"]}


@router.get("/api/citas")
async def api_citas(user: dict = Depends(requiere_panel)):
    if user["rol"] == "empleada":
        return await listar_citas(empleado_filtro=user["empleado_id"])
    return await listar_citas()


@router.get("/api/empleados")
async def api_empleados(_: dict = Depends(requiere_panel)):
    return await listar_empleados()


@router.get("/api/empleados/gestion")
async def api_empleados_gestion(user: dict = Depends(requiere_panel)):
    _solo_admin(user)
    return await gestionar_empleados()


@router.post("/api/empleados")
async def api_crear_empleado(payload: dict, user: dict = Depends(requiere_panel)):
    _solo_admin(user)
    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    return await crear_empleado(
        nombre,
        hora_inicio=payload.get("hora_inicio"),
        duracion_horas=payload.get("duracion_horas"),
        dias=payload.get("dias"),
    )


@router.post("/api/empleados/{empleado_id}/estado")
async def api_empleado_estado(empleado_id: str, payload: dict, user: dict = Depends(requiere_panel)):
    _solo_admin(user)
    if not await desactivar_empleado(empleado_id, bool(payload.get("activo"))):
        raise HTTPException(status_code=404, detail="Empleada no encontrada")
    return {"ok": True}


@router.post("/api/empleados/{empleado_id}/horario")
async def api_empleado_horario(empleado_id: str, payload: dict, user: dict = Depends(requiere_panel)):
    _solo_admin(user)
    dias = payload.get("dias") or []
    if not await establecer_horario_empleado(
        empleado_id, payload.get("hora_inicio"), payload.get("duracion_horas"), dias
    ):
        raise HTTPException(status_code=404, detail="Empleada no encontrada")
    return {"ok": True}


@router.delete("/api/empleados/{empleado_id}")
async def api_eliminar_empleado(empleado_id: str, user: dict = Depends(requiere_panel)):
    _solo_admin(user)
    if not await eliminar_empleado(empleado_id):
        raise HTTPException(status_code=404, detail="Empleada no encontrada")
    return {"ok": True}


@router.post("/api/citas/{cita_id}/estado")
async def api_estado(cita_id: str, payload: dict, _: dict = Depends(requiere_panel)):
    estado = payload.get("estado")
    if estado not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Estado inválido")
    if not await actualizar_cita(cita_id, estado=estado):
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return {"ok": True}


@router.post("/api/citas/{cita_id}/empleado")
async def api_empleado(cita_id: str, payload: dict, user: dict = Depends(requiere_panel)):
    _solo_admin(user)
    empleado_id = payload.get("empleado_id") or None
    if not await actualizar_cita(cita_id, empleado_id=empleado_id):
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return {"ok": True}


# ════════════════════════════════════════════════════════════
# Página (exige sesión; si no hay, manda al login)
# ════════════════════════════════════════════════════════════
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def panel_home(request: Request):
    user = await usuario_actual(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user["rol"] not in ("admin", "empleada"):
        raise HTTPException(status_code=403, detail="Sin acceso al panel")
    return _PAGINA_HTML


_PAGINA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MDnails · Panel</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
<style>
  :root{
    --rosa:#d6447a; --rosa-2:#b83267; --rosa-suave:#fdeef4; --rosa-borde:#f4d7e4;
    --tinta:#2a2230; --gris:#9a8f97; --bg:#fbf7f9; --panel:#ffffff; --linea:#f0e6ec;
    --ok:#1f9d6b; --warn:#c98a00; --bad:#d84a4a; --info:#3b73d6;
    --sombra:0 6px 24px rgba(120,40,80,.08);
  }
  *{box-sizing:border-box}
  html,body{margin:0}
  body{
    font-family:'Inter',system-ui,sans-serif; color:var(--tinta);
    background:
      radial-gradient(1200px 600px at 100% -10%, #fbe9f1 0%, transparent 55%),
      radial-gradient(900px 500px at -10% 0%, #f3ecfa 0%, transparent 50%),
      var(--bg);
    min-height:100vh;
  }
  header{
    position:sticky; top:0; z-index:20; backdrop-filter:saturate(1.2) blur(8px);
    background:rgba(255,255,255,.82); border-bottom:1px solid var(--linea);
    padding:14px 28px; display:flex; align-items:center; gap:14px; flex-wrap:wrap;
  }
  .marca{display:flex; align-items:center; gap:12px}
  .logo{
    width:42px; height:42px; border-radius:13px; display:grid; place-items:center;
    background:linear-gradient(135deg,var(--rosa),var(--rosa-2)); color:#fff; font-size:20px;
    box-shadow:0 6px 16px rgba(184,50,103,.35); animation:pop .5s ease both;
  }
  .marca h1{font-family:'Playfair Display',serif; font-size:20px; margin:0; line-height:1}
  .marca span{font-size:12px; color:var(--gris)}
  .vivo{margin-left:auto; display:flex; align-items:center; gap:8px; font-size:12px; color:var(--gris)}
  .usr{display:flex; align-items:center; gap:10px; font-size:13px}
  .usr b{color:var(--tinta)} .usr .rol{font-size:11px; color:var(--gris)}
  .salir{color:var(--rosa-2); text-decoration:none; font-weight:600; border:1px solid var(--rosa-borde); padding:6px 12px; border-radius:9px; transition:.15s}
  .salir:hover{background:var(--rosa-suave)}
  .oculto{display:none !important}
  .dot{width:9px; height:9px; border-radius:50%; background:var(--ok); box-shadow:0 0 0 0 rgba(31,157,107,.6); animation:pulse 1.8s infinite}
  main{max-width:1180px; margin:0 auto; padding:24px 28px 60px}
  /* Navegación */
  .nav{display:flex; align-items:center; gap:8px; margin-bottom:22px; flex-wrap:wrap}
  .navbtn{background:var(--panel); border:1px solid var(--linea); padding:9px 16px; border-radius:11px; cursor:pointer; font-weight:600; font-size:14px; color:var(--gris); font-family:inherit; box-shadow:var(--sombra); transition:.15s}
  .navbtn:hover{color:var(--rosa)}
  .navbtn.activo{background:linear-gradient(135deg,var(--rosa),var(--rosa-2)); color:#fff; border-color:transparent}
  .navlink{margin-left:auto; color:var(--rosa-2); font-weight:600; font-size:13px; text-decoration:none; border:1px dashed var(--rosa-borde); padding:8px 14px; border-radius:11px; transition:.15s}
  .navlink:hover{background:var(--rosa-suave)}
  .stats{display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px}
  .stat{background:var(--panel); border:1px solid var(--linea); border-radius:18px; padding:18px 20px; box-shadow:var(--sombra); animation:rise .5s ease both}
  .stat .n{font-size:30px; font-weight:700; font-family:'Playfair Display',serif; line-height:1}
  .stat .l{font-size:12.5px; color:var(--gris); margin-top:6px; text-transform:uppercase; letter-spacing:.05em}
  .stat.hoy .n{color:var(--rosa)} .stat.pend .n{color:var(--warn)}
  .stat.conf .n{color:var(--ok)} .stat.tot .n{color:var(--info)}
  .barra{display:flex; align-items:center; gap:10px; margin-bottom:16px; flex-wrap:wrap}
  .vtitulo{font-family:'Playfair Display',serif; font-size:20px; margin:0}
  .chips{display:inline-flex; background:var(--panel); border:1px solid var(--linea); border-radius:12px; padding:4px; gap:2px; box-shadow:var(--sombra)}
  .chip{border:none; background:transparent; padding:8px 16px; border-radius:9px; cursor:pointer; color:var(--gris); font-weight:600; font-size:13.5px; transition:.18s}
  .chip:hover{color:var(--rosa)}
  .chip.activo{background:linear-gradient(135deg,var(--rosa),var(--rosa-2)); color:#fff; box-shadow:0 4px 12px rgba(184,50,103,.3)}
  .btn{border:none; border-radius:11px; padding:9px 16px; cursor:pointer; font-weight:600; font-size:13.5px; transition:.18s; font-family:inherit}
  .btn.primary{background:linear-gradient(135deg,var(--rosa),var(--rosa-2)); color:#fff; box-shadow:0 4px 12px rgba(184,50,103,.3); margin-left:auto}
  .btn.primary:hover{transform:translateY(-1px); box-shadow:0 8px 18px rgba(184,50,103,.4)}
  .btn.ghost{background:#f4eef1; color:var(--tinta)}
  .tarjeta{background:var(--panel); border:1px solid var(--linea); border-radius:20px; box-shadow:var(--sombra); overflow:hidden}
  table{width:100%; border-collapse:collapse}
  th,td{text-align:left; padding:15px 18px; font-size:14px; vertical-align:middle}
  thead th{background:var(--rosa-suave); color:var(--rosa-2); font-size:11.5px; text-transform:uppercase; letter-spacing:.06em; font-weight:700}
  tbody tr{border-top:1px solid var(--linea); animation:rise .4s ease both}
  tbody tr:hover{background:#fdf9fb}
  .hora-h{font-weight:700; font-size:15px}
  .hora-d{font-size:12px; color:var(--gris)}
  .hora-d::first-letter{text-transform:uppercase}
  .cli{font-weight:600}
  .tel{font-size:12px; color:var(--gris)}
  .badge{display:inline-block; padding:4px 12px; border-radius:999px; font-size:12px; font-weight:700; text-transform:capitalize}
  .b-pendiente{background:#fff4d6; color:#8a6a00}
  .b-confirmada{background:#d8f3e6; color:#0f6b46}
  .b-cancelada{background:#fbdada; color:#a32222}
  .b-completada{background:#dbe8ff; color:#23509e}
  select{font-family:inherit; font-size:13px; border:1px solid var(--linea); border-radius:9px; padding:7px 9px; background:#fff; color:var(--tinta); cursor:pointer; transition:.15s}
  select:hover{border-color:var(--rosa)}
  .estado-cell{display:flex; align-items:center; gap:10px; flex-wrap:wrap}
  .mini{border:1px solid var(--linea); background:#fff; border-radius:9px; padding:6px 11px; cursor:pointer; font-size:12.5px; font-weight:600; color:var(--tinta); font-family:inherit; transition:.15s}
  .mini:hover{border-color:var(--rosa)}
  .mini.bad{color:var(--bad); border-color:#f3c7c7}
  .mini.ok{color:var(--ok); border-color:#bfe6d3}
  .acc{display:flex; gap:8px; flex-wrap:wrap}
  .vacio{text-align:center; padding:60px 20px; color:var(--gris)}
  .vacio .ico{font-size:46px; opacity:.6}
  .vacio p{margin:12px 0 0; font-size:15px}
  .vacio a{color:var(--rosa); cursor:pointer; font-weight:600; text-decoration:underline}
  .skel{height:14px; border-radius:6px; background:linear-gradient(90deg,#f0e6ec 25%,#f8eef3 37%,#f0e6ec 63%); background-size:400% 100%; animation:shimmer 1.4s infinite}
  .overlay{position:fixed; inset:0; background:rgba(42,34,48,.45); backdrop-filter:blur(2px); display:none; place-items:center; z-index:50; animation:fade .2s ease}
  .overlay.open{display:grid}
  .modal{background:#fff; border-radius:20px; padding:26px; width:min(420px,92vw); box-shadow:0 20px 60px rgba(0,0,0,.25); animation:rise .25s ease}
  .modal h3{font-family:'Playfair Display',serif; margin:0 0 4px}
  .modal p{margin:0 0 16px; color:var(--gris); font-size:13.5px}
  .modal label{font-size:13px; font-weight:600; color:var(--gris); display:block; margin:0 0 6px}
  .modal input[type=text], .modal input[type=time]{width:100%; padding:11px 13px; border:1px solid var(--linea); border-radius:11px; font-family:inherit; font-size:14px; margin-bottom:14px}
  .modal input:focus{outline:none; border-color:var(--rosa)}
  .modal input[type=range]{width:100%; margin-bottom:16px}
  .dias{display:flex; gap:6px; flex-wrap:wrap; margin-bottom:16px}
  .diachk{display:flex; align-items:center; gap:5px; font-size:13px; border:1px solid var(--linea); padding:6px 10px; border-radius:9px; cursor:pointer}
  .fila{display:flex; gap:10px; justify-content:flex-end}
  #toasts{position:fixed; bottom:22px; right:22px; z-index:60; display:flex; flex-direction:column; gap:10px}
  .toast{background:var(--tinta); color:#fff; padding:12px 18px; border-radius:12px; font-size:13.5px; box-shadow:0 10px 30px rgba(0,0,0,.25); animation:slideIn .3s ease}
  .toast.ok{background:#1f9d6b} .toast.err{background:#d84a4a}
  @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(31,157,107,.5)}70%{box-shadow:0 0 0 9px rgba(31,157,107,0)}100%{box-shadow:0 0 0 0 rgba(31,157,107,0)}}
  @keyframes rise{from{opacity:0; transform:translateY(10px)}to{opacity:1; transform:none}}
  @keyframes pop{from{opacity:0; transform:scale(.6)}to{opacity:1; transform:none}}
  @keyframes fade{from{opacity:0}to{opacity:1}}
  @keyframes slideIn{from{opacity:0; transform:translateX(30px)}to{opacity:1; transform:none}}
  @keyframes shimmer{0%{background-position:100% 0}100%{background-position:-100% 0}}
  @keyframes fadeUp{from{opacity:0; transform:translateY(14px)} to{opacity:1; transform:none}}
  /* Flujo de animaciones e interacción */
  .anim{animation:fadeUp .4s cubic-bezier(.2,.7,.3,1) both}
  .stat{transition:transform .2s ease, box-shadow .2s ease}
  .stat:hover{transform:translateY(-3px); box-shadow:0 12px 30px rgba(120,40,80,.14)}
  .tarjeta{transition:box-shadow .25s ease}
  .tarjeta:hover{box-shadow:0 10px 32px rgba(120,40,80,.12)}
  .mini{transition:transform .12s ease, border-color .15s ease, color .15s ease}
  .mini:active{transform:scale(.93)}
  .btn:active{transform:scale(.97)}
  .navbtn:active{transform:scale(.96)}
  .chip:active{transform:scale(.95)}
  .badge{transition:transform .15s ease}
  tbody tr:hover .badge{transform:scale(1.06)}
  @media(max-width:760px){.stats{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<header>
  <div class="marca">
    <div class="logo">💅</div>
    <div><h1>MDnails</h1><span>Panel de administración</span></div>
  </div>
  <div class="vivo"><span class="dot"></span><span id="vivoTxt">conectando…</span></div>
  <div class="usr"><span><b id="usrNombre">…</b><div class="rol" id="usrRol"></div></span><a class="salir" href="/logout">Salir</a></div>
</header>

<main>
  <nav class="nav">
    <button class="navbtn activo" data-v="citas" onclick="verVista('citas')">📅 Citas</button>
    <button class="navbtn oculto" id="navEmpleadas" data-v="empleadas" onclick="verVista('empleadas')">👩 Empleadas</button>
    <a class="navlink" href="/reservar" target="_blank" rel="noopener">Ver portal de clientas ↗</a>
  </nav>

  <!-- ===== Vista Citas ===== -->
  <section id="vistaCitas">
    <section class="stats">
      <div class="stat hoy"><div class="n" id="sHoy">·</div><div class="l">Citas hoy</div></div>
      <div class="stat pend"><div class="n" id="sPend">·</div><div class="l">Pendientes</div></div>
      <div class="stat conf"><div class="n" id="sConf">·</div><div class="l">Confirmadas</div></div>
      <div class="stat tot"><div class="n" id="sTot">·</div><div class="l">Total</div></div>
    </section>
    <div class="barra">
      <div class="chips">
        <button class="chip activo" data-f="proximas" onclick="setFiltro('proximas')">Próximas</button>
        <button class="chip" data-f="hoy" onclick="setFiltro('hoy')">Hoy</button>
        <button class="chip" data-f="pendientes" onclick="setFiltro('pendientes')">Pendientes</button>
        <button class="chip" data-f="completadas" onclick="setFiltro('completadas')">Completadas</button>
        <button class="chip" data-f="todas" onclick="setFiltro('todas')">Todas</button>
      </div>
    </div>
    <div class="tarjeta">
      <table>
        <thead><tr><th>Hora</th><th>Cliente</th><th>Servicio</th><th>Empleada</th><th>Estado</th></tr></thead>
        <tbody id="tbody"></tbody>
      </table>
      <div class="vacio" id="vacio" style="display:none"></div>
    </div>
  </section>

  <!-- ===== Vista Empleadas ===== -->
  <section id="vistaEmpleadas" class="oculto">
    <div class="barra">
      <h2 class="vtitulo">Empleadas</h2>
      <button class="btn primary" onclick="abrirModalEmpleada('crear')">+ Nueva empleada</button>
    </div>
    <div class="tarjeta">
      <table>
        <thead><tr><th>Nombre</th><th>Turno</th><th>Estado</th><th>Acciones</th></tr></thead>
        <tbody id="tbodyEmp"></tbody>
      </table>
    </div>
  </section>
</main>

<!-- Modal empleada (crear / editar turno) -->
<div class="overlay" id="overlay">
  <div class="modal">
    <h3 id="modalTitulo">Nueva empleada</h3>
    <p id="modalSub">Define su nombre y su turno de trabajo.</p>
    <div id="campoNombre">
      <label>Nombre</label>
      <input type="text" id="inpEmpNombre" placeholder="Nombre de la empleada">
    </div>
    <label>Hora de entrada</label>
    <input type="time" id="inpHoraInicio" value="09:00">
    <label>Duración del turno: <b id="lblDur">8 horas</b></label>
    <input type="range" id="inpDur" min="1" max="10" value="8" oninput="document.getElementById('lblDur').textContent=this.value+(this.value==='1'?' hora':' horas')">
    <label>Días de trabajo</label>
    <div class="dias" id="diasBox"></div>
    <div class="fila">
      <button class="btn ghost" onclick="cerrarModal()">Cancelar</button>
      <button class="btn primary" style="margin:0" onclick="guardarEmpleadaForm()">Guardar</button>
    </div>
  </div>
</div>

<div id="toasts"></div>

<script>
const API = "/panel/api";
const TZ  = "America/Mazatlan";
const ESTADOS = ["pendiente","confirmada","cancelada","completada"];
const DIAS_ABREV = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"];
let filtro = "proximas", empleados = [], empleadosGestion = [], citas = [], huella = "", esAdmin = true;
let modoModal = "crear", editId = null;

async function api(path, opts){
  const r = await fetch(API + path, opts);
  if(!r.ok) throw new Error("HTTP " + r.status);
  return r.status === 204 ? null : r.json();
}
function toast(msg, tipo="ok"){
  const t = document.createElement("div");
  t.className = "toast " + tipo;
  t.textContent = (tipo==="ok"?"✓ ":"✕ ") + msg;
  document.getElementById("toasts").appendChild(t);
  setTimeout(()=>{ t.style.opacity=0; setTimeout(()=>t.remove(),300); }, 2600);
}
// ---- Formato de horas en 12h (AM/PM) ----
function ampm(hhmm){
  if(!hhmm) return "";
  const [H,M] = hhmm.split(":").map(Number);
  const d = new Date(); d.setHours(H, M, 0, 0);
  return d.toLocaleTimeString("es-MX",{hour:"numeric",minute:"2-digit",hour12:true});
}
function diasTexto(dias){
  if(!dias || !dias.length) return "Sin turno";
  const o = [...dias].sort((a,b)=>a-b);
  const contiguo = o.every((v,i)=> i===0 || v===o[i-1]+1);
  return (contiguo && o.length>1)
    ? `${DIAS_ABREV[o[0]]}–${DIAS_ABREV[o[o.length-1]]}`
    : o.map(d=>DIAS_ABREV[d]).join(", ");
}
function fechaLocal(iso){ return new Date(iso).toLocaleDateString("es-MX",{timeZone:TZ,year:"numeric",month:"2-digit",day:"2-digit"}); }
function esHoy(iso){ return fechaLocal(iso) === fechaLocal(new Date().toISOString()); }
function fmt(iso){
  const d = new Date(iso);
  return {
    h: d.toLocaleTimeString("es-MX",{timeZone:TZ,hour:"numeric",minute:"2-digit",hour12:true}),
    d: d.toLocaleDateString("es-MX",{timeZone:TZ,weekday:"long",day:"2-digit",month:"short"})
  };
}
function optsEmpleadas(sel){
  return '<option value="">— sin asignar —</option>' +
    empleados.map(e=>`<option value="${e.id}" ${e.id===sel?"selected":""}>${e.nombre}</option>`).join("");
}
function optsEstado(act){ return ESTADOS.map(s=>`<option value="${s}" ${s===act?"selected":""}>${s}</option>`).join(""); }

// ---- Navegación entre vistas ----
function verVista(v){
  document.getElementById("vistaCitas").classList.toggle("oculto", v!=="citas");
  document.getElementById("vistaEmpleadas").classList.toggle("oculto", v!=="empleadas");
  document.querySelectorAll(".navbtn").forEach(b=>b.classList.toggle("activo", b.dataset.v===v));
  const sec = document.getElementById(v==="citas" ? "vistaCitas" : "vistaEmpleadas");
  sec.classList.remove("anim"); void sec.offsetWidth; sec.classList.add("anim");  // re-dispara la animación
  if(v==="empleadas") recargarEmpleados();
}

// ---- Citas ----
function setFiltro(f){
  filtro = f; huella = "";
  document.querySelectorAll(".chip").forEach(c=>c.classList.toggle("activo", c.dataset.f===f));
  pintar();
}
async function cambiarEstado(id, estado){
  try{ await api(`/citas/${id}/estado`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({estado})});
    toast("Estado actualizado"); await cargar(true);
  }catch(e){ toast("No se pudo actualizar","err"); }
}
async function cambiarEmpleada(id, empleado_id){
  try{ await api(`/citas/${id}/empleado`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({empleado_id})});
    toast("Empleada asignada"); await cargar(true);
  }catch(e){ toast("No se pudo asignar","err"); }
}
function stats(){
  document.getElementById("sHoy").textContent  = citas.filter(c=>esHoy(c.inicia_en)).length;
  document.getElementById("sPend").textContent = citas.filter(c=>c.estado==="pendiente").length;
  document.getElementById("sConf").textContent = citas.filter(c=>c.estado==="confirmada").length;
  document.getElementById("sTot").textContent  = citas.length;
}
function aplicarFiltro(){
  if(filtro==="proximas"){
    const hoy = new Date(); hoy.setHours(0,0,0,0);   // desde el inicio de hoy en adelante
    return citas.filter(c=>new Date(c.inicia_en) >= hoy && c.estado!=="completada" && c.estado!=="cancelada");
  }
  if(filtro==="hoy")        return citas.filter(c=>esHoy(c.inicia_en) && c.estado!=="completada");
  if(filtro==="pendientes") return citas.filter(c=>c.estado==="pendiente");
  if(filtro==="completadas")return citas.filter(c=>c.estado==="completada");
  return citas;
}
function pintar(){
  stats();
  const lista = aplicarFiltro();
  const tbody = document.getElementById("tbody");
  const vacio = document.getElementById("vacio");
  if(!lista.length){
    tbody.innerHTML = "";
    vacio.style.display = "block";
    const hayOtras = citas.length > 0;
    vacio.innerHTML = `<div class="ico">🗓️</div><p>No hay citas en esta vista.` +
      (hayOtras && filtro!=="todas" ? ` Tienes ${citas.length} en total — <a onclick="setFiltro('todas')">ver todas</a>.` : ``) + `</p>`;
    return;
  }
  vacio.style.display = "none";
  tbody.innerHTML = lista.map((c,i)=>{
    const t = fmt(c.inicia_en);
    return `<tr style="animation-delay:${i*40}ms">
      <td><div class="hora-h">${t.h}</div><div class="hora-d">${t.d}</div></td>
      <td><div class="cli">${c.cliente}</div><div class="tel">${c.telefono}</div></td>
      <td>${c.servicio}</td>
      <td><select onchange="cambiarEmpleada('${c.id}',this.value)" ${esAdmin?'':'disabled'}>${optsEmpleadas(c.empleado_id)}</select></td>
      <td><div class="estado-cell">
        <span class="badge b-${c.estado}">${c.estado}</span>
        <select onchange="cambiarEstado('${c.id}',this.value)">${optsEstado(c.estado)}</select>
      </div></td>
    </tr>`;
  }).join("");
}
async function cargar(forzar){
  try{
    const data = await api("/citas");
    citas = Array.isArray(data) ? data : [];
    const h = JSON.stringify(citas) + filtro;
    if(forzar || h !== huella){ huella = h; pintar(); }
    const ahora = new Date().toLocaleTimeString("es-MX",{timeZone:TZ,hour:"numeric",minute:"2-digit",hour12:true});
    document.getElementById("vivoTxt").textContent = "En vivo · " + ahora;
  }catch(e){
    document.getElementById("vivoTxt").textContent = "Sin conexión…";
  }
}

// ---- Empleadas ----
async function recargarEmpleados(){
  try{
    empleadosGestion = await api("/empleados/gestion");
    empleados = await api("/empleados");
    renderEmpleados();
  }catch(e){ /* la empleada no admin no entra aquí */ }
}
function renderEmpleados(){
  const cont = document.getElementById("tbodyEmp");
  if(!empleadosGestion.length){
    cont.innerHTML = `<tr><td colspan="4" style="text-align:center;color:var(--gris);padding:34px">Aún no hay empleadas. Agrega la primera con “+ Nueva empleada”.</td></tr>`;
    return;
  }
  cont.innerHTML = empleadosGestion.map(e=>{
    const turno = e.hora_inicio ? `${diasTexto(e.dias)} · ${ampm(e.hora_inicio)} – ${ampm(e.hora_fin)}` : "Sin turno asignado";
    const estado = e.activo ? `<span class="badge b-confirmada">activa</span>` : `<span class="badge b-cancelada">baja</span>`;
    const baja = e.activo
      ? `<button class="mini bad" onclick="toggleBaja('${e.id}',false)">Dar de baja</button>`
      : `<button class="mini ok" onclick="toggleBaja('${e.id}',true)">Reactivar</button><button class="mini bad" onclick="eliminarEmpleado('${e.id}')">Eliminar</button>`;
    return `<tr style="${e.activo?'':'opacity:.55'}">
      <td><b>${e.nombre}</b></td>
      <td>${turno}</td>
      <td>${estado}</td>
      <td><div class="acc"><button class="mini" onclick="editarTurno('${e.id}')">Editar turno</button>${baja}</div></td>
    </tr>`;
  }).join("");
}
function construirDias(seleccion){
  document.getElementById("diasBox").innerHTML = DIAS_ABREV.map((d,i)=>
    `<label class="diachk"><input type="checkbox" value="${i}" ${seleccion.includes(i)?"checked":""}> ${d}</label>`).join("");
}
function abrirModalEmpleada(modo, emp){
  modoModal = modo; editId = emp ? emp.id : null;
  document.getElementById("modalTitulo").textContent = modo==="crear" ? "Nueva empleada" : "Editar turno";
  document.getElementById("modalSub").textContent = modo==="crear" ? "Define su nombre y su turno de trabajo." : `Ajusta el turno de ${emp.nombre}.`;
  document.getElementById("campoNombre").style.display = modo==="crear" ? "block" : "none";
  document.getElementById("inpEmpNombre").value = "";
  document.getElementById("inpHoraInicio").value = (emp && emp.hora_inicio) ? emp.hora_inicio : "09:00";
  const dur = (emp && emp.duracion_horas) ? emp.duracion_horas : 8;
  document.getElementById("inpDur").value = dur;
  document.getElementById("lblDur").textContent = dur + (dur===1 ? " hora" : " horas");
  construirDias((emp && emp.dias && emp.dias.length) ? emp.dias : [0,1,2,3,4,5]);
  document.getElementById("overlay").classList.add("open");
}
function editarTurno(id){
  const e = empleadosGestion.find(x=>x.id===id);
  if(e) abrirModalEmpleada("editar", e);
}
function cerrarModal(){ document.getElementById("overlay").classList.remove("open"); }
async function guardarEmpleadaForm(){
  const hora_inicio = document.getElementById("inpHoraInicio").value;
  const duracion_horas = parseInt(document.getElementById("inpDur").value);
  const dias = [...document.querySelectorAll("#diasBox input:checked")].map(c=>parseInt(c.value));
  if(!dias.length){ toast("Selecciona al menos un día de trabajo","err"); return; }
  try{
    if(modoModal==="crear"){
      const nombre = document.getElementById("inpEmpNombre").value.trim();
      if(!nombre){ toast("Escribe el nombre de la empleada","err"); return; }
      await api("/empleados",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({nombre, hora_inicio, duracion_horas, dias})});
      toast("Empleada agregada");
    }else{
      await api(`/empleados/${editId}/horario`,{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({hora_inicio, duracion_horas, dias})});
      toast("Turno actualizado");
    }
    cerrarModal(); await recargarEmpleados();
  }catch(e){ toast("No se pudo guardar","err"); }
}
async function toggleBaja(id, activo){
  if(!activo && !confirm("¿Dar de baja a esta empleada? Ya no se le podrán asignar citas nuevas (puedes reactivarla después).")) return;
  try{
    await api(`/empleados/${id}/estado`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({activo})});
    toast(activo ? "Empleada reactivada" : "Empleada dada de baja");
    await recargarEmpleados();
  }catch(e){ toast("No se pudo cambiar el estado","err"); }
}
async function eliminarEmpleado(id){
  const e = empleadosGestion.find(x=>x.id===id);
  const nombre = e ? e.nombre : "esta empleada";
  if(!confirm(`¿Eliminar permanentemente a ${nombre}? Esta acción NO se puede deshacer. Sus citas pasadas quedarán sin empleada asignada.`)) return;
  try{
    await api(`/empleados/${id}`,{method:"DELETE"});
    toast("Empleada eliminada");
    await recargarEmpleados();
  }catch(e){ toast("No se pudo eliminar","err"); }
}

// ---- Inicio ----
(async function init(){
  try{
    const yo = await api("/yo");
    esAdmin = yo.rol === "admin";
    document.getElementById("usrNombre").textContent = yo.nombre || "Usuaria";
    document.getElementById("usrRol").textContent = esAdmin ? "Administrador(a)" : "Empleada";
    if(esAdmin) document.getElementById("navEmpleadas").classList.remove("oculto");
  }catch(e){ location.href = "/login"; return; }
  document.getElementById("tbody").innerHTML = Array.from({length:3}).map(()=>
    `<tr><td colspan="5"><div class="skel"></div></td></tr>`).join("");
  if(esAdmin){ try{ empleados = await api("/empleados"); }catch(e){ empleados = []; } }
  await cargar(true);
  setInterval(()=>cargar(false), 7000);
})();
</script>
</body>
</html>
"""

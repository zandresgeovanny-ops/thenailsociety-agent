# agent/panel.py — Panel de administración de citas (dashboard web)
# Generado por AgentKit

"""
Dashboard interno para las empleadas del salón. Lo sirve el propio backend
(FastAPI) y está protegido con autenticación básica (usuario/contraseña), de
modo que los datos de las clientas nunca quedan expuestos públicamente.

Acceso de datos del lado del servidor (vía memory.py), que usa la conexión
directa a Postgres y por lo tanto no depende de las políticas RLS de Supabase.
"""

import os
import secrets
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse

from agent.memory import (
    listar_citas, listar_empleados, crear_empleado, actualizar_cita,
)

logger = logging.getLogger("agentkit")

router = APIRouter(prefix="/panel")
security = HTTPBasic()

PANEL_USER = os.getenv("PANEL_USER", "admin")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD", "")

ESTADOS_VALIDOS = {"pendiente", "confirmada", "cancelada", "completada"}


def verificar(credenciales: HTTPBasicCredentials = Depends(security)) -> str:
    """Valida usuario y contraseña. Si PANEL_PASSWORD no está configurada, bloquea el acceso."""
    user_ok = secrets.compare_digest(credenciales.username, PANEL_USER)
    pass_ok = bool(PANEL_PASSWORD) and secrets.compare_digest(credenciales.password, PANEL_PASSWORD)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            detail="No autorizado",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credenciales.username


# ════════════════════════════════════════════════════════════
# API JSON (consumida por la página)
# ════════════════════════════════════════════════════════════
@router.get("/api/citas")
async def api_citas(_: str = Depends(verificar)):
    return await listar_citas()


@router.get("/api/empleados")
async def api_empleados(_: str = Depends(verificar)):
    return await listar_empleados()


@router.post("/api/empleados")
async def api_crear_empleado(payload: dict, _: str = Depends(verificar)):
    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    return await crear_empleado(nombre)


@router.post("/api/citas/{cita_id}/estado")
async def api_estado(cita_id: str, payload: dict, _: str = Depends(verificar)):
    estado = payload.get("estado")
    if estado not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Estado inválido")
    if not await actualizar_cita(cita_id, estado=estado):
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return {"ok": True}


@router.post("/api/citas/{cita_id}/empleado")
async def api_empleado(cita_id: str, payload: dict, _: str = Depends(verificar)):
    empleado_id = payload.get("empleado_id") or None
    if not await actualizar_cita(cita_id, empleado_id=empleado_id):
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return {"ok": True}


# ════════════════════════════════════════════════════════════
# Página del panel
# ════════════════════════════════════════════════════════════
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def panel_home(_: str = Depends(verificar)):
    return _PAGINA_HTML


_PAGINA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MDnails — Panel de citas</title>
<style>
  :root { --rosa:#d6336c; --rosa-suave:#fce4ec; --bg:#faf7f8; --texto:#2b2b2b; --gris:#8a8a8a; --linea:#eadfe3; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background:var(--bg); color:var(--texto); }
  header { background:#fff; border-bottom:1px solid var(--linea); padding:16px 24px; display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
  header h1 { font-size:18px; margin:0; color:var(--rosa); }
  header .logo { font-size:22px; }
  .controles { margin-left:auto; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  .estado-conexion { font-size:12px; color:var(--gris); }
  button, select { font-family:inherit; font-size:14px; }
  .btn { background:var(--rosa); color:#fff; border:none; border-radius:8px; padding:8px 14px; cursor:pointer; }
  .btn.sec { background:#fff; color:var(--rosa); border:1px solid var(--rosa); }
  .toggle { display:inline-flex; border:1px solid var(--linea); border-radius:8px; overflow:hidden; }
  .toggle button { background:#fff; border:none; padding:8px 14px; cursor:pointer; color:var(--gris); }
  .toggle button.activo { background:var(--rosa-suave); color:var(--rosa); font-weight:600; }
  main { padding:24px; }
  table { width:100%; border-collapse:collapse; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,.05); }
  th, td { text-align:left; padding:12px 14px; border-bottom:1px solid var(--linea); font-size:14px; vertical-align:middle; }
  th { background:var(--rosa-suave); color:var(--rosa); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
  tr:last-child td { border-bottom:none; }
  .hora-dia { font-weight:600; }
  .hora-fecha { font-size:12px; color:var(--gris); }
  .tel { font-size:12px; color:var(--gris); }
  .badge { display:inline-block; padding:3px 10px; border-radius:999px; font-size:12px; font-weight:600; }
  .b-pendiente { background:#fff3cd; color:#8a6d3b; }
  .b-confirmada { background:#d1e7dd; color:#0f5132; }
  .b-cancelada { background:#f8d7da; color:#842029; }
  .b-completada { background:#cfe2ff; color:#084298; }
  select { border:1px solid var(--linea); border-radius:8px; padding:6px 8px; background:#fff; }
  .vacio { text-align:center; color:var(--gris); padding:48px; }
</style>
</head>
<body>
<header>
  <span class="logo">💅</span>
  <h1>MDnails — Panel de citas</h1>
  <div class="controles">
    <span class="estado-conexion" id="estadoConexion">cargando…</span>
    <div class="toggle">
      <button id="fHoy" class="activo" onclick="setFiltro('hoy')">Hoy</button>
      <button id="fTodas" onclick="setFiltro('todas')">Todas</button>
    </div>
    <button class="btn sec" onclick="agregarEmpleada()">+ Empleada</button>
  </div>
</header>
<main>
  <table>
    <thead>
      <tr><th>Hora</th><th>Cliente</th><th>Servicio</th><th>Empleada</th><th>Estado</th></tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <div class="vacio" id="vacio" style="display:none">No hay citas para mostrar.</div>
</main>

<script>
const TZ = "America/Mazatlan";
let filtro = "hoy";
let empleados = [];
let ultimaData = "";   // para no re-renderizar si nada cambió

function setFiltro(f) {
  filtro = f;
  document.getElementById("fHoy").classList.toggle("activo", f === "hoy");
  document.getElementById("fTodas").classList.toggle("activo", f === "todas");
  ultimaData = "";  // forzar re-render
  cargar();
}

function esHoy(iso) {
  const fmt = (d) => d.toLocaleDateString("es-MX", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });
  return fmt(new Date(iso)) === fmt(new Date());
}

function fmtHora(iso) {
  const d = new Date(iso);
  const dia = d.toLocaleDateString("es-MX", { timeZone: TZ, weekday: "short", day: "2-digit", month: "short" });
  const hora = d.toLocaleTimeString("es-MX", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
  return { dia, hora };
}

function opcionesEmpleadas(seleccionado) {
  let html = '<option value="">— sin asignar —</option>';
  for (const e of empleados) {
    const sel = e.id === seleccionado ? "selected" : "";
    html += `<option value="${e.id}" ${sel}>${e.nombre}</option>`;
  }
  return html;
}

function opcionesEstado(actual) {
  return ["pendiente", "confirmada", "cancelada", "completada"]
    .map(s => `<option value="${s}" ${s === actual ? "selected" : ""}>${s}</option>`).join("");
}

async function cambiarEstado(id, estado) {
  await fetch(`api/citas/${id}/estado`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ estado }) });
  ultimaData = ""; cargar();
}
async function cambiarEmpleada(id, empleado_id) {
  await fetch(`api/citas/${id}/empleado`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ empleado_id }) });
  ultimaData = ""; cargar();
}

async function agregarEmpleada() {
  const nombre = prompt("Nombre de la empleada:");
  if (!nombre) return;
  await fetch("api/empleados", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nombre }) });
  empleados = await (await fetch("api/empleados")).json();
  ultimaData = ""; cargar();
}

function render(citas) {
  const tbody = document.getElementById("tbody");
  const vacio = document.getElementById("vacio");
  const lista = filtro === "hoy" ? citas.filter(c => esHoy(c.inicia_en)) : citas;
  vacio.style.display = lista.length ? "none" : "block";
  tbody.innerHTML = lista.map(c => {
    const { dia, hora } = fmtHora(c.inicia_en);
    return `<tr>
      <td><div class="hora-dia">${hora}</div><div class="hora-fecha">${dia}</div></td>
      <td>${c.cliente}<div class="tel">${c.telefono}</div></td>
      <td>${c.servicio}</td>
      <td><select onchange="cambiarEmpleada('${c.id}', this.value)">${opcionesEmpleadas(c.empleado_id)}</select></td>
      <td>
        <span class="badge b-${c.estado}">${c.estado}</span>
        <select onchange="cambiarEstado('${c.id}', this.value)" style="margin-top:6px;display:block">${opcionesEstado(c.estado)}</select>
      </td>
    </tr>`;
  }).join("");
}

async function cargar() {
  try {
    const citas = await (await fetch("api/citas")).json();
    const huella = JSON.stringify(citas) + filtro;
    if (huella !== ultimaData) { ultimaData = huella; render(citas); }
    const ahora = new Date().toLocaleTimeString("es-MX", { timeZone: TZ, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    document.getElementById("estadoConexion").textContent = "actualizado " + ahora;
  } catch (e) {
    document.getElementById("estadoConexion").textContent = "sin conexión…";
  }
}

(async function init() {
  empleados = await (await fetch("api/empleados")).json();
  await cargar();
  setInterval(cargar, 5000);  // auto-refresco cada 5 segundos
})();
</script>
</body>
</html>
"""

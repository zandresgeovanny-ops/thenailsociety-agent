# agent/panel.py — Panel de administración (citas y empleadas)
# Generado por AgentKit

"""
Dashboard interno del salón, servido por el backend (FastAPI) y protegido con
sesión por roles. El admin gestiona citas y empleadas; la empleada solo ve su
agenda. Los datos se leen del lado del servidor (no se exponen públicamente).
"""

import uuid
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError

from agent.memory import (
    listar_citas, listar_empleados, crear_empleado, actualizar_cita,
    desactivar_empleado, establecer_horario_empleado, gestionar_empleados,
    eliminar_empleado, registro_citas, catalogo_servicios,
    buscar_empleada_disponible, buscar_o_crear_cliente, guardar_cita, ZONA_SALON,
)
from agent.auth import usuario_actual, requiere_panel
from agent.branding import aplicar_marca

logger = logging.getLogger("agentkit")

router = APIRouter(prefix="/panel")

ESTADOS_VALIDOS = {"pendiente", "confirmada", "cancelada", "completada", "no_show"}


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


@router.get("/api/registro")
async def api_registro(user: dict = Depends(requiere_panel)):
    # La empleada ve solo las citas que ella atendió; el admin ve todas.
    if user["rol"] == "empleada":
        return await registro_citas(empleado_filtro=user["empleado_id"])
    return await registro_citas()


@router.get("/api/servicios")
async def api_servicios(_: dict = Depends(requiere_panel)):
    return await catalogo_servicios()


@router.post("/api/citas")
async def api_crear_cita(payload: dict, user: dict = Depends(requiere_panel)):
    """Agendar una cita manualmente desde el panel (walk-in / clienta que llama)."""
    _solo_admin(user)
    nombre = (payload.get("nombre") or "").strip()
    telefono = (payload.get("telefono") or "").strip()
    servicio_id = payload.get("servicio_id")
    empleado_id = payload.get("empleado_id") or None
    fecha = payload.get("fecha")
    hora = payload.get("hora")
    if not all([nombre, telefono, servicio_id, fecha, hora]):
        raise HTTPException(status_code=400, detail="Faltan datos para la cita")

    servicios = await catalogo_servicios()
    servicio = next((s for s in servicios if s["id"] == servicio_id), None)
    if servicio is None:
        raise HTTPException(status_code=400, detail="Servicio inválido")
    try:
        inicia_en = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M").replace(tzinfo=ZONA_SALON)
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha u hora inválida")
    termina_en = inicia_en + timedelta(minutes=servicio["duracion_min"])

    # Si no se eligió empleada, intentar asignar una libre automáticamente
    if not empleado_id:
        disp = await buscar_empleada_disponible(inicia_en, termina_en)
        empleado_id = disp["empleado_id"]  # libre o None (el admin la asigna luego)

    cliente_id = await buscar_o_crear_cliente(telefono, nombre)
    try:
        await guardar_cita(
            cliente_id=cliente_id, servicio_id=uuid.UUID(servicio_id),
            inicia_en=inicia_en, termina_en=termina_en,
            empleado_id=uuid.UUID(empleado_id) if empleado_id else None,
            notas=f"Agendada desde el panel · {servicio['nombre']}", origen="panel",
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Esa empleada ya tiene una cita a esa hora.")
    return {"ok": True}


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
    return aplicar_marca(_PAGINA_HTML)


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
    --rosa:#e8308f; --rosa-2:#c41f73; --rosa-suave:#2a1830; --rosa-borde:#4a2f44;
    --tinta:#f1ebf5; --gris:#9d92aa; --bg:#141019; --panel:#221c2b; --linea:#352c40;
    --ok:#2ecb8f; --warn:#e0a52a; --bad:#ef6b6b; --info:#5b9bf0;
    --sombra:0 10px 30px rgba(0,0,0,.45);
  }
  *{box-sizing:border-box}
  html,body{margin:0}
  body{
    font-family:'Inter',system-ui,sans-serif; color:var(--tinta);
    background:
      radial-gradient(1200px 600px at 100% -10%, rgba(232,48,143,.16) 0%, transparent 55%),
      radial-gradient(900px 500px at -10% 0%, rgba(150,48,160,.14) 0%, transparent 50%),
      var(--bg);
    min-height:100vh;
  }
  header{
    position:sticky; top:0; z-index:20; backdrop-filter:saturate(1.2) blur(8px);
    background:rgba(28,22,36,.82); border-bottom:1px solid var(--linea);
    padding:14px 28px; display:flex; align-items:center; gap:14px; flex-wrap:wrap;
  }
  .marca{display:flex; align-items:center; gap:12px}
  .logo{
    width:46px; height:46px; border-radius:50%;
    box-shadow:0 0 0 1px var(--linea), 0 6px 16px rgba(232,48,143,.3); animation:pop .5s ease both;
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
  .busqueda{margin-left:auto; padding:9px 14px; border:1px solid var(--linea); border-radius:11px; font-family:inherit; font-size:13.5px; min-width:min(280px,60vw); transition:border-color .15s; background:#1b1622; color:var(--tinta)}
  .busqueda::placeholder{color:#6f6580}
  .busqueda:focus{outline:none; border-color:var(--rosa)}
  .resumen-reg{display:flex; gap:14px; margin-bottom:16px; flex-wrap:wrap}
  .resumen-reg .pill{background:var(--rosa-suave); color:var(--rosa); border-radius:13px; padding:10px 18px; font-size:13.5px; font-weight:600; box-shadow:var(--sombra)}
  .resumen-reg .pill b{font-family:'Playfair Display',serif; font-size:19px; margin-left:4px}
  .costo{font-weight:700; color:var(--rosa-2)}
  .tarjeta.grafica{padding:18px 20px 8px; margin-bottom:16px}
  .grafica-titulo{font-weight:600; color:var(--rosa-2); font-size:12px; text-transform:uppercase; letter-spacing:.05em; margin-bottom:6px}
  #graficaReg rect{transition:opacity .15s} #graficaReg rect:hover{opacity:.82}
  .chips{display:inline-flex; background:var(--panel); border:1px solid var(--linea); border-radius:12px; padding:4px; gap:2px; box-shadow:var(--sombra)}
  .chip{border:none; background:transparent; padding:8px 16px; border-radius:9px; cursor:pointer; color:var(--gris); font-weight:600; font-size:13.5px; transition:.18s}
  .chip:hover{color:var(--rosa)}
  .chip.activo{background:linear-gradient(135deg,var(--rosa),var(--rosa-2)); color:#fff; box-shadow:0 4px 12px rgba(184,50,103,.3)}
  .btn{border:none; border-radius:11px; padding:9px 16px; cursor:pointer; font-weight:600; font-size:13.5px; transition:.18s; font-family:inherit}
  .btn.primary{background:linear-gradient(135deg,var(--rosa),var(--rosa-2)); color:#fff; box-shadow:0 4px 12px rgba(184,50,103,.3); margin-left:auto}
  .btn.primary:hover{transform:translateY(-1px); box-shadow:0 8px 18px rgba(184,50,103,.4)}
  .btn.ghost{background:#2a2433; color:var(--tinta)}
  .tarjeta{background:var(--panel); border:1px solid var(--linea); border-radius:20px; box-shadow:var(--sombra); overflow:hidden}
  table{width:100%; border-collapse:collapse}
  th,td{text-align:left; padding:15px 18px; font-size:14px; vertical-align:middle}
  thead th{background:var(--rosa-suave); color:var(--rosa); font-size:11.5px; text-transform:uppercase; letter-spacing:.06em; font-weight:700}
  tbody tr{border-top:1px solid var(--linea); animation:rise .4s ease both}
  tbody tr:hover{background:#2a2336}
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
  .b-no_show{background:#ece8f4; color:#5b4a8a}
  select{font-family:inherit; font-size:13px; border:1px solid var(--linea); border-radius:9px; padding:7px 9px; background:#1b1622; color:var(--tinta); cursor:pointer; transition:.15s}
  select:hover{border-color:var(--rosa)}
  .estado-cell{display:flex; align-items:center; gap:10px; flex-wrap:wrap}
  .mini{border:1px solid var(--linea); background:#1b1622; border-radius:9px; padding:6px 11px; cursor:pointer; font-size:12.5px; font-weight:600; color:var(--tinta); font-family:inherit; transition:.15s}
  .mini:hover{border-color:var(--rosa)}
  .mini.bad{color:var(--bad); border-color:#f3c7c7}
  .mini.ok{color:var(--ok); border-color:#bfe6d3}
  .acc{display:flex; gap:8px; flex-wrap:wrap}
  .vacio{text-align:center; padding:60px 20px; color:var(--gris)}
  .vacio .ico{font-size:46px; opacity:.6}
  .vacio p{margin:12px 0 0; font-size:15px}
  .vacio a{color:var(--rosa); cursor:pointer; font-weight:600; text-decoration:underline}
  .skel{height:14px; border-radius:6px; background:linear-gradient(90deg,#241f2e 25%,#2e2738 37%,#241f2e 63%); background-size:400% 100%; animation:shimmer 1.4s infinite}
  .overlay{position:fixed; inset:0; background:rgba(42,34,48,.45); backdrop-filter:blur(2px); display:none; place-items:center; z-index:50; animation:fade .2s ease}
  .overlay.open{display:grid}
  .modal{background:var(--panel); border:1px solid var(--linea); border-radius:20px; padding:26px; width:min(420px,92vw); box-shadow:0 24px 60px rgba(0,0,0,.55); animation:rise .25s ease}
  .modal h3{font-family:'Playfair Display',serif; margin:0 0 4px}
  .modal p{margin:0 0 16px; color:var(--gris); font-size:13.5px}
  .modal label{font-size:13px; font-weight:600; color:var(--gris); display:block; margin:0 0 6px}
  .modal input[type=text], .modal input[type=time], .modal input[type=password]{width:100%; padding:11px 13px; border:1px solid var(--linea); border-radius:11px; font-family:inherit; font-size:14px; margin-bottom:14px; background:#1b1622; color:var(--tinta)}
  .modal input::placeholder{color:#6f6580}
  .modal input:focus{outline:none; border-color:var(--rosa)}
  .modal input[type=range]{width:100%; margin-bottom:16px}
  .modal input[type=date]{width:100%; padding:11px 13px; border:1px solid var(--linea); border-radius:11px; font-family:inherit; font-size:14px; margin-bottom:14px; background:#1b1622; color:var(--tinta)}
  .modal select.sel-full{width:100%; padding:11px 13px; border:1px solid var(--linea); border-radius:11px; font-family:inherit; font-size:14px; margin-bottom:14px; background:#1b1622; color:var(--tinta)}
  .dias{display:flex; gap:6px; flex-wrap:wrap; margin-bottom:16px}
  .diachk{display:flex; align-items:center; gap:5px; font-size:13px; border:1px solid var(--linea); padding:6px 10px; border-radius:9px; cursor:pointer}
  .fila{display:flex; gap:10px; justify-content:flex-end}
  #toasts{position:fixed; bottom:22px; right:22px; z-index:60; display:flex; flex-direction:column; gap:10px}
  .toast{background:#2a2433; color:#fff; border:1px solid var(--linea); padding:12px 18px; border-radius:12px; font-size:13.5px; box-shadow:0 10px 30px rgba(0,0,0,.45); animation:slideIn .3s ease}
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
    <img class="logo" src="__LOGO__" alt="MD nails">
    <div><h1>MD nails</h1><span>Panel de administración</span></div>
  </div>
  <div class="vivo"><span class="dot"></span><span id="vivoTxt">conectando…</span></div>
  <div class="usr"><span><b id="usrNombre">…</b><div class="rol" id="usrRol"></div></span><a class="salir" style="cursor:pointer" onclick="abrirPass()">Contraseña</a><a class="salir" href="/logout">Salir</a></div>
</header>

<main>
  <nav class="nav">
    <button class="navbtn activo" data-v="citas" onclick="verVista('citas')">📅 Citas</button>
    <button class="navbtn" data-v="registro" onclick="verVista('registro')">📋 Registro</button>
    <button class="navbtn oculto" id="navEmpleadas" data-v="empleadas" onclick="verVista('empleadas')">👩 Empleadas</button>
    <a class="navlink" href="/reservar" target="_blank" rel="noopener">Ver portal de clientas ↗</a>
  </nav>

  <!-- ===== Vista Citas ===== -->
  <section id="vistaCitas">
    <section class="stats">
      <div class="stat hoy"><div class="n" id="sHoy">·</div><div class="l">Citas hoy</div></div>
      <div class="stat pend"><div class="n" id="sPend">·</div><div class="l">Pendientes</div></div>
      <div class="stat conf"><div class="n" id="sConf">·</div><div class="l">Confirmadas</div></div>
      <div class="stat tot"><div class="n" id="sTot">·</div><div class="l">Completadas</div></div>
    </section>
    <div class="barra">
      <div class="chips">
        <button class="chip activo" data-f="proximas" onclick="setFiltro('proximas')">Próximas</button>
        <button class="chip" data-f="hoy" onclick="setFiltro('hoy')">Hoy</button>
        <button class="chip" data-f="pendientes" onclick="setFiltro('pendientes')">Pendientes</button>
        <button class="chip" data-f="completadas" onclick="setFiltro('completadas')">Completadas</button>
        <button class="chip" data-f="todas" onclick="setFiltro('todas')">Todas</button>
      </div>
      <button class="btn primary oculto" id="btnNuevaCita" onclick="abrirModalCita()">+ Nueva cita</button>
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

  <!-- ===== Vista Registro (citas completadas) ===== -->
  <section id="vistaRegistro" class="oculto">
    <div class="barra">
      <h2 class="vtitulo">Registro e ingresos</h2>
      <input id="busqRegistro" class="busqueda" placeholder="Buscar por cliente, servicio o empleada…" oninput="renderRegistro()">
      <button class="btn primary" style="margin:0" onclick="exportarCSV()">⬇ Exportar a Excel</button>
    </div>
    <div class="resumen-reg" id="resumenReg"></div>
    <div class="tarjeta grafica" id="cardGrafica">
      <div class="grafica-titulo">Ingresos por mes</div>
      <div id="graficaReg"></div>
    </div>
    <div class="tarjeta">
      <table>
        <thead><tr><th>Cita</th><th>Servicio</th><th>Costo</th><th>Empleada</th><th>Cliente</th><th>Agendada</th></tr></thead>
        <tbody id="tbodyReg"></tbody>
      </table>
      <div class="vacio" id="vacioReg" style="display:none"></div>
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

<!-- Modal nueva cita (agendar manual) -->
<div class="overlay" id="overlayCita">
  <div class="modal">
    <h3>Nueva cita</h3>
    <p>Agenda a una clienta que llamó o llegó al salón.</p>
    <label>Nombre de la clienta</label>
    <input type="text" id="citaNombre" placeholder="Ej. María López">
    <label>WhatsApp / teléfono</label>
    <input type="text" id="citaTel" placeholder="Ej. 6671234567">
    <label>Servicio</label>
    <select id="citaServicio" class="sel-full"></select>
    <label>Empleada</label>
    <select id="citaEmpleada" class="sel-full"></select>
    <label>Día</label>
    <input type="date" id="citaFecha">
    <label>Hora</label>
    <input type="time" id="citaHora" value="10:00">
    <div class="fila">
      <button class="btn ghost" onclick="cerrarModalCita()">Cancelar</button>
      <button class="btn primary" style="margin:0" onclick="guardarCita()">Agendar</button>
    </div>
  </div>
</div>

<!-- Modal cambiar contraseña -->
<div class="overlay" id="overlayPass">
  <div class="modal">
    <h3>Cambiar contraseña</h3>
    <p>Tu nueva contraseña debe tener al menos 8 caracteres.</p>
    <label>Contraseña actual</label>
    <input type="password" id="passActual" autocomplete="current-password">
    <label>Nueva contraseña</label>
    <input type="password" id="passNueva" autocomplete="new-password">
    <div class="fila">
      <button class="btn ghost" onclick="document.getElementById('overlayPass').classList.remove('open')">Cancelar</button>
      <button class="btn primary" style="margin:0" onclick="guardarPass()">Guardar</button>
    </div>
  </div>
</div>

<div id="toasts"></div>

<script>
const API = "/panel/api";
const TZ  = "America/Mazatlan";
const ESTADOS = ["pendiente","confirmada","completada","cancelada","no_show"];
const ESTADO_LABEL = {pendiente:"pendiente", confirmada:"confirmada", completada:"completada", cancelada:"cancelada", no_show:"no llegó"};
const DIAS_ABREV = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"];
const MESES_AB = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
let filtro = "proximas", empleados = [], empleadosGestion = [], citas = [], registro = [], servicios = [], huella = "", esAdmin = true;
let modoModal = "crear", editId = null;

async function api(path, opts){
  const r = await fetch(API + path, opts);
  if(!r.ok) throw new Error("HTTP " + r.status);
  return r.status === 204 ? null : r.json();
}
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}[c];});}
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
    empleados.map(e=>`<option value="${e.id}" ${e.id===sel?"selected":""}>${esc(e.nombre)}</option>`).join("");
}
function optsEstado(act){ return ESTADOS.map(s=>`<option value="${s}" ${s===act?"selected":""}>${ESTADO_LABEL[s]}</option>`).join(""); }

// ---- Navegación entre vistas ----
function verVista(v){
  const vistas = {citas:"vistaCitas", registro:"vistaRegistro", empleadas:"vistaEmpleadas"};
  Object.entries(vistas).forEach(([k,id])=> document.getElementById(id).classList.toggle("oculto", k!==v));
  document.querySelectorAll(".navbtn").forEach(b=>b.classList.toggle("activo", b.dataset.v===v));
  const sec = document.getElementById(vistas[v]);
  if(sec){ sec.classList.remove("anim"); void sec.offsetWidth; sec.classList.add("anim"); }  // re-dispara la animación
  if(v==="empleadas") recargarEmpleados();
  if(v==="registro") cargarRegistro();
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
  // "Citas hoy" = activas de hoy (sin completadas/canceladas), para que cuadre con la lista
  document.getElementById("sHoy").textContent  = citas.filter(c=>esHoy(c.inicia_en) && c.estado!=="completada" && c.estado!=="cancelada").length;
  document.getElementById("sPend").textContent = citas.filter(c=>c.estado==="pendiente").length;
  document.getElementById("sConf").textContent = citas.filter(c=>c.estado==="confirmada").length;
  document.getElementById("sTot").textContent  = citas.filter(c=>c.estado==="completada").length;
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
      <td><div class="cli">${esc(c.cliente)}</div><div class="tel">${esc(c.telefono)}</div></td>
      <td>${esc(c.servicio)}</td>
      <td><select onchange="cambiarEmpleada('${c.id}',this.value)" ${esAdmin?'':'disabled'}>${optsEmpleadas(c.empleado_id)}</select></td>
      <td><div class="estado-cell">
        <span class="badge b-${c.estado}">${ESTADO_LABEL[c.estado]||c.estado}</span>
        ${c.estado!=="completada"?`<button class="mini ok" title="Marcar completada" onclick="cambiarEstado('${c.id}','completada')">✓ Completar</button>`:""}
        ${c.estado!=="no_show"?`<button class="mini bad" title="La clienta no llegó" onclick="cambiarEstado('${c.id}','no_show')">No llegó</button>`:""}
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
      <td><b>${esc(e.nombre)}</b></td>
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

// ---- Registro de citas completadas ----
async function cargarRegistro(){
  try{ registro = await api("/registro"); }catch(e){ registro = []; }
  renderGrafica();
  renderRegistro();
}
function renderGrafica(){
  const cont = document.getElementById("graficaReg");
  const porMes = {};
  registro.forEach(r=>{
    const ym = new Date(r.inicia_en).toLocaleDateString("en-CA",{timeZone:TZ}).slice(0,7); // YYYY-MM
    porMes[ym] = (porMes[ym] || 0) + (r.costo || 0);
  });
  const meses = Object.keys(porMes).sort().slice(-8);  // últimos 8 meses
  if(!meses.length){
    document.getElementById("cardGrafica").style.display = "none";
    return;
  }
  document.getElementById("cardGrafica").style.display = "";
  const max = Math.max(...meses.map(m=>porMes[m])) || 1;
  const H = 210, padB = 36, padT = 26, bw = 46;
  const W = Math.max(meses.length * 78, 300);
  const gap = (W - meses.length * bw) / (meses.length + 1);
  let bars = "";
  meses.forEach((m,i)=>{
    const val = porMes[m];
    const h = (H - padB - padT) * (val / max);
    const x = gap + i * (bw + gap), y = H - padB - h;
    const etiqueta = MESES_AB[parseInt(m.split("-")[1]) - 1];
    bars += `<rect x="${x}" y="${y}" width="${bw}" height="${h}" rx="8" fill="url(#gradReg)"></rect>`;
    bars += `<text x="${x+bw/2}" y="${y-8}" text-anchor="middle" font-size="12.5" font-weight="700" fill="#b83267">$${val.toLocaleString("es-MX")}</text>`;
    bars += `<text x="${x+bw/2}" y="${H-12}" text-anchor="middle" font-size="12.5" fill="#9a8f97">${etiqueta}</text>`;
  });
  cont.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%; max-width:${W}px; height:auto; display:block">
    <defs><linearGradient id="gradReg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#d6447a"/><stop offset="100%" stop-color="#b83267"/></linearGradient></defs>
    ${bars}</svg>`;
}
function exportarCSV(){
  const cab = ["Fecha cita","Hora","Servicio","Costo","Empleada","Cliente","Telefono","Agendada el"];
  const filas = [cab];
  registro.forEach(r=>{
    const d = new Date(r.inicia_en);
    filas.push([
      d.toLocaleDateString("es-MX",{timeZone:TZ}),
      d.toLocaleTimeString("es-MX",{timeZone:TZ,hour:"2-digit",minute:"2-digit",hour12:true}),
      r.servicio,
      r.costo != null ? r.costo : "",
      r.empleada || "",
      r.cliente,
      r.telefono,
      new Date(r.agendada_en).toLocaleDateString("es-MX",{timeZone:TZ}),
    ]);
  });
  const csv = filas.map(f=>f.map(c=>`"${String(c).replace(/"/g,'""')}"`).join(",")).join("\\r\\n");
  const blob = new Blob(["\\ufeff" + csv], {type:"text/csv;charset=utf-8"});  // BOM para que Excel lea acentos
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "registro-mdnails.csv"; a.click();
  URL.revokeObjectURL(url);
  toast("Archivo descargado");
}
function renderRegistro(){
  const q = (document.getElementById("busqRegistro").value || "").toLowerCase().trim();
  const lista = registro.filter(r => !q || `${r.cliente} ${r.servicio} ${r.empleada||""}`.toLowerCase().includes(q));
  const total = lista.reduce((s,r)=> s + (r.costo||0), 0);
  document.getElementById("resumenReg").innerHTML =
    `<div class="pill">Servicios realizados: <b>${lista.length}</b></div>` +
    `<div class="pill">Ingresos: <b>$${total.toLocaleString("es-MX")}</b></div>`;
  const tb = document.getElementById("tbodyReg");
  const vac = document.getElementById("vacioReg");
  if(!lista.length){
    tb.innerHTML = "";
    vac.style.display = "block";
    vac.innerHTML = `<div class="ico">📋</div><p>Aún no hay citas completadas en el registro.</p>`;
    return;
  }
  vac.style.display = "none";
  tb.innerHTML = lista.map((r,i)=>{
    const t = fmt(r.inicia_en);
    const agend = new Date(r.agendada_en).toLocaleDateString("es-MX",{timeZone:TZ,day:"2-digit",month:"short",year:"numeric"});
    const costo = (r.costo!=null) ? `$${r.costo.toLocaleString("es-MX")}` : "—";
    return `<tr style="animation-delay:${i*35}ms">
      <td><div class="hora-h">${t.h}</div><div class="hora-d">${t.d}</div></td>
      <td>${esc(r.servicio)}</td>
      <td><span class="costo">${costo}</span></td>
      <td>${esc(r.empleada || "— sin asignar —")}</td>
      <td><div class="cli">${esc(r.cliente)}</div><div class="tel">${esc(r.telefono)}</div></td>
      <td>${agend}</td>
    </tr>`;
  }).join("");
}

// ---- Agendar cita manual (admin) ----
function abrirModalCita(){
  document.getElementById("citaNombre").value = "";
  document.getElementById("citaTel").value = "";
  document.getElementById("citaServicio").innerHTML = servicios.map(s=>
    `<option value="${s.id}">${esc(s.nombre)} · $${s.precio!=null?s.precio:0} (${s.duracion_min} min)</option>`).join("");
  document.getElementById("citaEmpleada").innerHTML =
    `<option value="">Asignar automáticamente</option>` + empleados.map(e=>`<option value="${e.id}">${esc(e.nombre)}</option>`).join("");
  document.getElementById("citaFecha").value = new Date().toLocaleDateString("en-CA",{timeZone:TZ});
  document.getElementById("citaHora").value = "10:00";
  document.getElementById("overlayCita").classList.add("open");
}
function cerrarModalCita(){ document.getElementById("overlayCita").classList.remove("open"); }
async function guardarCita(){
  const datos = {
    nombre: document.getElementById("citaNombre").value.trim(),
    telefono: document.getElementById("citaTel").value.trim(),
    servicio_id: document.getElementById("citaServicio").value,
    empleado_id: document.getElementById("citaEmpleada").value || null,
    fecha: document.getElementById("citaFecha").value,
    hora: document.getElementById("citaHora").value,
  };
  if(!datos.nombre || !datos.telefono || !datos.fecha || !datos.hora){ toast("Completa nombre, teléfono, día y hora","err"); return; }
  try{
    await api("/citas",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(datos)});
    cerrarModalCita(); toast("Cita agendada"); await cargar(true);
  }catch(e){ toast("No se pudo agendar (¿horario ocupado?)","err"); }
}

// ---- Cambiar contraseña ----
function abrirPass(){
  document.getElementById("passActual").value="";
  document.getElementById("passNueva").value="";
  document.getElementById("overlayPass").classList.add("open");
}
async function guardarPass(){
  const actual=document.getElementById("passActual").value, nueva=document.getElementById("passNueva").value;
  if(nueva.length<8){ toast("La nueva contraseña debe tener al menos 8 caracteres","err"); return; }
  try{
    const r=await fetch("/mi-password",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({actual,nueva})});
    if(!r.ok) throw 0;
    document.getElementById("overlayPass").classList.remove("open");
    toast("Contraseña actualizada");
  }catch(e){ toast("No se pudo cambiar (¿la actual es correcta?)","err"); }
}

// ---- Inicio ----
(async function init(){
  try{
    const yo = await api("/yo");
    esAdmin = yo.rol === "admin";
    document.getElementById("usrNombre").textContent = yo.nombre || "Usuaria";
    document.getElementById("usrRol").textContent = esAdmin ? "Administrador(a)" : "Empleada";
    if(esAdmin){
      document.getElementById("navEmpleadas").classList.remove("oculto");
      document.getElementById("btnNuevaCita").classList.remove("oculto");
    }
  }catch(e){ location.href = "/login"; return; }
  document.getElementById("tbody").innerHTML = Array.from({length:3}).map(()=>
    `<tr><td colspan="5"><div class="skel"></div></td></tr>`).join("");
  if(esAdmin){ try{ empleados = await api("/empleados"); servicios = await api("/servicios"); }catch(e){ empleados = []; servicios = []; } }
  await cargar(true);
  setInterval(()=>cargar(false), 7000);
})();
</script>
</body>
</html>
"""

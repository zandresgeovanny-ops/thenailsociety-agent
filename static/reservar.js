// static/reservar.js — Portal de reservas para clientas
// Externalizado desde reservas.py para permitir una CSP estricta (sin scripts ni
// manejadores inline). Los clics se gestionan por delegación con atributos data-act.
const API = "/reservar/api";
const TZ = "America/Mazatlan";
let paso = 1;
let servicios = [], empleados = [];
const sel = { servicio:null, empleado:null, empleadoNombre:"Cualquiera disponible", fecha:null, hora:null };

async function api(p, opts){ const r = await fetch(API+p, opts); if(!r.ok){ const e=await r.json().catch(()=>({})); throw new Error(e.detail||("HTTP "+r.status)); } return r.json(); }
// Escapa texto para insertarlo de forma segura en HTML (evita XSS con nombres del salón)
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
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
    html += `<div class="cat">${esc(cat)}</div>`;
    for(const s of servicios.filter(x=>x.categoria===cat)){
      const precio = s.precio!=null ? `$${esc(s.precio)}` : "";
      html += `<div class="opt ${sel.servicio===s.id?'sel':''}" data-act="servicio" data-id="${esc(s.id)}">
        <div class="info"><div class="n">${esc(s.nombre)}</div><div class="meta">${esc(s.duracion_min)} min</div></div>
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
    <div class="nav"><button class="btn ghost" data-act="back" data-to="servicios">Atrás</button></div></div>`;
  if(!empleados.length) empleados = await api("/empleados");
  let html = `<div class="opt ${sel.empleado===null?'sel':''}" data-act="empleado">
      <div class="avatar">✨</div><div class="info"><div class="n">Cualquiera disponible</div><div class="meta">El salón asigna</div></div></div>`;
  for(const e of empleados){
    html += `<div class="opt ${sel.empleado===e.id?'sel':''}" data-act="empleado" data-id="${esc(e.id)}">
      <div class="avatar">${esc(e.nombre[0])}</div><div class="info"><div class="n">${esc(e.nombre)}</div></div></div>`;
  }
  document.getElementById("lista").innerHTML = html;
}
// Solo se pasa el id (un UUID seguro); el nombre se busca aquí para no inyectarlo en el HTML
function elegirEmpleado(id){
  const e = id ? empleados.find(x=>x.id===id) : null;
  sel.empleado = id;
  sel.empleadoNombre = e ? e.nombre : "Cualquiera disponible";
  sel.hora = null;
  pintarFecha();
}

// ---------- Paso 3: fecha y hora ----------
function pintarFecha(){
  paso=3; marcarPasos();
  const c = document.getElementById("contenido");
  c.innerHTML = `<div class="panel"><h2>Fecha y hora</h2><p class="sub">Elige el día y un horario disponible.</p>
    <label>Día</label><input type="date" id="fecha" min="${hoyISO()}" value="${sel.fecha||hoyISO()}" data-act="fecha">
    <label>Horarios disponibles</label><div id="slots"></div>
    <div class="nav"><button class="btn ghost" data-act="back" data-to="empleados">Atrás</button></div></div>`;
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
    cont.innerHTML = `<div class="slots">${slots.map(h=>`<div class="slot" data-act="hora" data-h="${esc(h)}">${ampm(h)}</div>`).join("")}</div>`;
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
    <div class="resumen">💅 <b>${esc(s.nombre)}</b> (${esc(s.duracion_min)} min)<br>👩 ${esc(sel.empleadoNombre)}<br>📅 ${f}<br>🕒 ${ampm(sel.hora)}</div>
    <label>Tu nombre</label><input type="text" id="nombre" placeholder="Ej. Mariana López">
    <label>Tu WhatsApp</label><input type="tel" id="telefono" placeholder="Ej. 6671234567">
    <div class="nav">
      <button class="btn ghost" data-act="back" data-to="fecha">Atrás</button>
      <button class="btn primary" id="btnOk" data-act="confirmar">Confirmar cita</button>
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
  }catch(e){ btn.disabled=false; btn.textContent="Confirmar cita"; alert(e.message); }
}
function pintarExito(nombre){
  const s = servicios.find(x=>x.id===sel.servicio);
  const f = new Date(sel.fecha+"T12:00:00").toLocaleDateString("es-MX",{weekday:"long",day:"numeric",month:"long"});
  document.getElementById("contenido").innerHTML = `<div class="panel exito">
    <div class="check">✓</div><h2>¡Cita reservada!</h2>
    <p class="sub">Gracias ${esc(nombre)}, te esperamos.<br><b>${esc(s.nombre)}</b> · ${f} · ${ampm(sel.hora)}</p>
    <div class="nav"><button class="btn primary" data-act="reload">Reservar otra</button></div></div>`;
}

// ---------- Delegación de eventos (CSP estricta: sin onclick/onchange inline) ----------
document.addEventListener("click", function(e){
  const t = e.target.closest("[data-act]");
  if(!t) return;
  switch(t.dataset.act){
    case "servicio": elegirServicio(t.dataset.id); break;
    case "empleado": elegirEmpleado(t.dataset.id || null); break;
    case "hora": elegirHora(t.dataset.h, t); break;
    case "back":
      if(t.dataset.to==="servicios") pintarServicios();
      else if(t.dataset.to==="empleados") pintarEmpleados();
      else if(t.dataset.to==="fecha") pintarFecha();
      break;
    case "confirmar": confirmar(); break;
    case "reload": location.reload(); break;
  }
});
document.addEventListener("change", function(e){
  if(e.target && e.target.dataset && e.target.dataset.act==="fecha") cargarSlots();
});

pintarServicios();

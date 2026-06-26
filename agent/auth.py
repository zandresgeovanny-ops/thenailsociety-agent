# agent/auth.py — Autenticación y roles (admin / empleada / clienta)
# Generado por AgentKit

"""
Autenticación propia, del lado del servidor:
- Contraseñas hasheadas con PBKDF2-SHA256 (librería estándar, sin dependencias).
- Sesión en una cookie firmada con HMAC (no se puede falsificar sin la SECRET_KEY).
- Dependencias para proteger rutas y exigir un rol.

La SECRET_KEY debe configurarse en producción (variable de entorno SECRET_KEY).
"""

import os
import hmac
import base64
import hashlib
import secrets
import logging

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from agent.memory import obtener_usuario_por_email, obtener_usuario_por_id, actualizar_password
from agent.branding import aplicar_marca
from agent.seguridad import limitar

logger = logging.getLogger("agentkit")
router = APIRouter()

# Clave para firmar la cookie de sesión. SIEMPRE configurar SECRET_KEY en Railway.
# Si no está, se usa una aleatoria por proceso (segura, pero cierra las sesiones al
# reiniciar). Nunca un valor por defecto conocido (sería falsificable).
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    logger.warning("SECRET_KEY no configurada: usando una temporal. Configúrala en Railway para sesiones persistentes.")
COOKIE = "sesion"
ES_PROD = os.getenv("ENVIRONMENT", "development") == "production"
ITERACIONES = 200_000


# ---------- Hash de contraseñas ----------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, almacenado: str) -> bool:
    try:
        _, iteraciones, salt_b64, hash_b64 = almacenado.split("$")
        salt = base64.b64decode(salt_b64)
        esperado = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iteraciones))
        return hmac.compare_digest(dk, esperado)
    except Exception:
        return False


# ---------- Cookie de sesión firmada ----------
def _firmar(uid: str) -> str:
    firma = hmac.new(SECRET_KEY.encode(), uid.encode(), hashlib.sha256).hexdigest()
    return f"{uid}.{firma}"


def _leer_token(token: str) -> str | None:
    try:
        uid, firma = token.rsplit(".", 1)
        esperada = hmac.new(SECRET_KEY.encode(), uid.encode(), hashlib.sha256).hexdigest()
        return uid if hmac.compare_digest(esperada, firma) else None
    except Exception:
        return None


async def usuario_actual(request: Request) -> dict | None:
    """Devuelve el usuario de la sesión (o None si no hay sesión válida)."""
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    uid = _leer_token(token)
    return await obtener_usuario_por_id(uid) if uid else None


async def requiere_panel(request: Request) -> dict:
    """Dependencia para la API del panel: exige sesión de admin o empleada."""
    user = await usuario_actual(request)
    if not user:
        raise HTTPException(status_code=401, detail="Sesión requerida")
    if user["rol"] not in ("admin", "empleada"):
        raise HTTPException(status_code=403, detail="Sin permiso")
    return user


# ---------- Rutas de login / logout ----------
@router.post("/login")
async def login(payload: dict, request: Request):
    limitar(request, "login", maximo=10, ventana_seg=300)  # anti fuerza bruta
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    user = await obtener_usuario_por_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    resp = JSONResponse({"ok": True, "rol": user["rol"], "nombre": user["nombre"]})
    resp.set_cookie(
        COOKIE, _firmar(user["id"]),
        httponly=True, secure=ES_PROD, samesite="lax", max_age=60 * 60 * 12,  # 12 h
    )
    return resp


@router.get("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie(COOKIE)
    return resp


@router.post("/mi-password")
async def cambiar_mi_password(payload: dict, request: Request):
    """Permite a cualquier usuario en sesión cambiar su propia contraseña."""
    user = await usuario_actual(request)
    if not user:
        raise HTTPException(status_code=401, detail="Sesión requerida")
    actual = payload.get("actual") or ""
    nueva = payload.get("nueva") or ""
    if not verify_password(actual, user["password_hash"]):
        raise HTTPException(status_code=403, detail="Tu contraseña actual no es correcta")
    if len(nueva) < 8:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 8 caracteres")
    await actualizar_password(user["id"], hash_password(nueva))
    return {"ok": True}


@router.get("/login", response_class=HTMLResponse)
async def pagina_login():
    return aplicar_marca(_PAGINA_LOGIN)


_PAGINA_LOGIN = """<!DOCTYPE html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MDnails · Iniciar sesión</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
<style>
  :root{--mag:#e8308f;--mag-2:#c41f73;--tinta:#f1ebf5;--gris:#9d92aa;--linea:#352c40;--panel:#221c2b;--bg:#141019}
  *{box-sizing:border-box}
  body{margin:0;min-height:100vh;display:grid;place-items:center;font-family:'Inter',system-ui,sans-serif;color:var(--tinta);
    background:radial-gradient(720px 420px at 50% -10%, rgba(232,48,143,.20), transparent 60%), var(--bg)}
  .card{background:var(--panel);border:1px solid var(--linea);border-radius:22px;box-shadow:0 24px 60px rgba(0,0,0,.55);padding:34px 30px;width:min(380px,92vw);animation:rise .4s ease both}
  .logo{width:96px;height:96px;display:block;margin:0 auto 10px;border-radius:50%;box-shadow:0 0 0 1px var(--linea),0 12px 32px rgba(232,48,143,.28)}
  .sub{text-align:center;color:var(--gris);font-size:13.5px;margin:6px 0 22px}
  label{font-size:13px;font-weight:600;color:var(--gris);display:block;margin-bottom:6px}
  input{width:100%;padding:12px 13px;border:1.5px solid var(--linea);border-radius:12px;font-family:inherit;font-size:15px;margin-bottom:14px;background:#1b1622;color:var(--tinta)}
  input::placeholder{color:#6f6580}
  input:focus{outline:none;border-color:var(--mag)}
  button{width:100%;border:none;border-radius:13px;padding:13px;font-weight:700;font-size:15px;cursor:pointer;color:#fff;font-family:inherit;background:linear-gradient(135deg,var(--mag),var(--mag-2));box-shadow:0 8px 22px rgba(232,48,143,.4);transition:.15s}
  button:hover{transform:translateY(-1px)}
  button:disabled{opacity:.5}
  .err{background:#3a1620;color:#ff9bb0;border:1px solid #5a2030;border-radius:10px;padding:10px 12px;font-size:13px;margin-bottom:14px;display:none}
  @keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
</style></head>
<body>
<form class="card" onsubmit="entrar(event)">
  <img class="logo" src="__LOGO__" alt="MD nails">
  <p class="sub">Panel de gestión · inicia sesión</p>
  <div class="err" id="err"></div>
  <label>Correo</label>
  <input type="email" id="email" placeholder="tucorreo@mdnails.com" required autofocus>
  <label>Contraseña</label>
  <input type="password" id="password" placeholder="••••••••" required>
  <button id="btn" type="submit">Entrar</button>
  <p style="text-align:center;color:var(--gris);font-size:12px;margin:14px 0 0">¿Olvidaste tu contraseña? Pídele a tu administrador que la restablezca.</p>
</form>
<script>
async function entrar(e){
  e.preventDefault();
  const btn=document.getElementById("btn"); const err=document.getElementById("err");
  btn.disabled=true; btn.textContent="Entrando..."; err.style.display="none";
  try{
    const r=await fetch("/login",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({email:document.getElementById("email").value,password:document.getElementById("password").value})});
    if(!r.ok){ const d=await r.json().catch(()=>({})); throw new Error(d.detail||"Error"); }
    location.href="/panel";
  }catch(ex){ err.textContent=ex.message; err.style.display="block"; btn.disabled=false; btn.textContent="Entrar"; }
}
</script>
</body></html>
"""

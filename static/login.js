// static/login.js — Lógica del formulario de inicio de sesión
// Externalizado desde auth.py para permitir una CSP estricta (sin scripts inline).
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
document.getElementById("formLogin").addEventListener("submit", entrar);

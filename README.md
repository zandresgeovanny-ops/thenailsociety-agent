# The Nail Society Spa — web + agente de WhatsApp

> **Si no te acuerdas de nada, este es el único archivo que necesitas abrir.**
> Aquí está qué es cada pieza, dónde vive, y qué comando corres para lanzar o
> actualizar. Todo lo demás del repo es código.

---

## 1. Qué es esto

Tres cosas que comparten la misma base de datos:

| Pieza | Qué hace | Quién la usa |
|---|---|---|
| **Web pública** | Enseña la carta, el equipo y las reseñas. Permite reservar. | Las clientas |
| **Agente de WhatsApp** | Contesta, agenda citas y manda recordatorios. Se llama **Sofía**. | Las clientas |
| **Panel** | Ver y mover la agenda, editar servicios y precios. | El salón |

El salón: **The Nail Society Spa**, Aguascalientes. Dos sucursales, Norte y Sur.
Instagram [@thenailsociety_ags](https://instagram.com/thenailsociety_ags).

---

## 2. Dónde vive cada cosa

| Servicio | Para qué | Dónde entrar |
|---|---|---|
| **Railway** | Corre el backend Python 24/7 | Proyecto `devoted-harmony`, servicio `thenailsociety-agent` |
| **Supabase** | La base de datos (citas, servicios, equipo) | Proyecto `thenailsociety`, región `us-west-1` |
| **Vercel** | Sirve la web pública | Equipo `Andrés' projects`, Root Directory = `web` |
| **Twilio** | Manda y recibe los WhatsApp | Sandbox de WhatsApp |
| **Anthropic** | El cerebro de Sofía (`claude-sonnet-4-6`) | console.anthropic.com |

**URLs vivas**

- Backend / API: `https://thenailsociety.up.railway.app`
- Salud del backend: `https://thenailsociety.up.railway.app/` → debe responder `{"status":"ok"}`
- Panel del salón: `https://thenailsociety.up.railway.app/panel`
- Web pública: `https://thenailsociety-agent-3lmx.vercel.app`

---

## 3. Cómo lanzar la web (primera vez)

**Paso 1 — Subir los cambios.** Abre el Explorador en `C:\Users\zandr\whatsapp-agentkit`,
haz clic en la barra de dirección, escribe `powershell` y Enter. Luego, una línea a la vez:

```powershell
git add web/
git commit -m "describe aqui que cambiaste"
git push tns main
```

**Paso 2 — Conectar Vercel.** En vercel.com → **Add New… → Project** → importas
`thenailsociety-agent`. Lo único que hay que tocar: **Root Directory = `web`**.
Después, **Deploy**.

**Paso 3 — Abrir el CORS.** En Railway → servicio `thenailsociety-agent` → Variables →
`ORIGENES_WEB` = `https://TU-DOMINIO.vercel.app,http://localhost:5173`.

Sin este paso la web carga pero Servicios, Equipo y Reseñas salen vacíos: el
backend rechaza al navegador por seguridad.

---

## 4. Cómo actualizar (todas las demás veces)

```powershell
git add web/
git commit -m "describe aqui que cambiaste"
git push tns main
```

Vercel redespliega solo. No hay que tocar nada más.

Para cambiar **precios, servicios, horarios o el equipo**: no se toca código.
Se hace desde el panel, o directo en Supabase.

---

## 5. Probar en tu computadora antes de subir

```powershell
cd web
npm install      # solo la primera vez
npm run dev      # abre http://localhost:5173
```

Para probar a Sofía sin WhatsApp, desde la carpeta raíz:

```powershell
python tests/test_local.py
```

---

## 6. Problemas frecuentes

**`fatal: Unable to create '.git/index.lock': File exists`**
Un candado de Git que quedó abandonado. No hay ningún proceso corriendo.

```powershell
Remove-Item .git\index.lock -Force
```

**La web carga pero Servicios y Equipo salen vacíos**
Es el CORS. Revisa que `ORIGENES_WEB` en Railway incluya el dominio exacto de
Vercel, con `https://` y **sin** barra al final.

**Sofía no contesta en WhatsApp**
Revisa en Twilio que el webhook apunte a
`https://thenailsociety.up.railway.app/webhook`, método POST.

**No sé si el backend está vivo**
Abre `https://thenailsociety.up.railway.app/` en el navegador. Si responde
`{"status":"ok"}`, está bien.

---

## 7. Cuidado con estas dos cosas

**El remoto de Git.** Este repo tiene tres. Sube siempre a **`tns`**, que es el
de The Nail Society. `origin` es el AgentKit original de otra persona.

**Los secretos.** Las claves reales viven en Railway, nunca en el código. El
archivo `.env` de tu computadora es solo para desarrollo local y `.gitignore`
lo excluye. Si alguna vez ves una clave dentro de un archivo `.md` o `.tsx`,
está mal puesta.

---

## 8. La marca

Antes de escribir cualquier texto o tocar un color, lee
`knowledge/thenailsociety_brand_voice.md`. Ahí está la voz, el tono, la paleta
y el vocabulario reales, sacados de su Instagram.

Tres reglas que se rompen seguido:

1. **El dorado nunca es color de texto** — no alcanza el contraste mínimo. Vive
   en bordes, filetes e iconos. Cuando hace falta dorado legible se usa la
   variante bronce `--acento-texto`.
2. **Nada de colores saturados.** La paleta es marfil, dorado y negro. Ni
   naranjas, ni neones, ni en las uñas del modelo 3D.
3. **Cero invención.** Precios, servicios, horarios y reseñas salen de la base
   de datos o de `knowledge/`. Si un dato no está, se pregunta.

---

## 9. Estructura del repo

```
agent/           Backend Python: webhook, cerebro, memoria, reservas, panel
config/          Datos del negocio y el system prompt de Sofía
knowledge/       Guía de marca, reseñas, imágenes, modelo 3D
migrations/      El esquema y los datos de Supabase, en orden
web/             La web pública (React + Vite) — esto es lo que sirve Vercel
  src/datos/     Contenido separado del código (para reusar la plantilla)
  src/secciones/ Hero, Servicios, Equipo, Reseñas, Sucursales, Reserva
scripts/         Utilidades sueltas (onboarding, simular Twilio)
```

`CLAUDE.md` son las instrucciones para Claude Code, no documentación del
proyecto. No hace falta que lo leas.

---

## 10. Reutilizar esto para otro cliente

La web está preparada para revenderse a una barbería, una clínica o un spa.
Lo que se cambia:

1. El bloque `--acento*` en `web/src/index.css` — es el único color de marca.
2. Los archivos de `web/src/datos/` — el contenido.
3. `config/business.yaml` y `config/prompts.yaml` — el negocio y la voz del agente.
4. Las migraciones, con el catálogo del cliente nuevo.

El objetivo es que un cliente nuevo no obligue a tocar ningún componente.
Todavía no está al 100%: parte del copy sigue dentro de los `.tsx`.

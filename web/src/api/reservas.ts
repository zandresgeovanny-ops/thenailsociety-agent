// Cliente de la API de reservas de The Nail Society Spa.
// Habla con el backend FastAPI existente (agent/reservas.py) vía VITE_API_URL.
// En desarrollo, si no hay VITE_API_URL, usa el proxy de Vite hacia :8000.

const BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");
const api = (ruta: string) => `${BASE}/reservar/api${ruta}`;

export interface Servicio {
  id: string;
  nombre: string;
  categoria: string;
  duracion_min: number;
  precio: number | null;
}

export interface Empleado {
  id: string;
  nombre: string;
  sucursal_id: string | null;
  especialidad: string | null;
}

export interface Sucursal {
  id: string;
  nombre: string;
  direccion: string | null;
  telefono: string | null;
}

export interface DatosReserva {
  nombre: string;
  telefono: string;
  servicio_id: string;
  sucursal_id?: string | null;
  empleado_id?: string | null;
  fecha: string; // YYYY-MM-DD
  hora: string; // HH:MM
}

async function pedir<T>(url: string, opciones?: RequestInit): Promise<T> {
  const r = await fetch(url, opciones);
  if (!r.ok) {
    let detalle = `Error ${r.status}`;
    try {
      const cuerpo = await r.json();
      detalle = cuerpo.detail || detalle;
    } catch {
      /* respuesta sin JSON */
    }
    throw new Error(detalle);
  }
  return r.json() as Promise<T>;
}

export const obtenerServicios = () => pedir<Servicio[]>(api("/servicios"));

export const obtenerSucursales = () => pedir<Sucursal[]>(api("/sucursales"));

export const obtenerEmpleados = () => pedir<Empleado[]>(api("/empleados"));

export async function obtenerDisponibilidad(params: {
  servicio_id: string;
  fecha: string;
  empleado_id?: string | null;
  sucursal_id?: string | null;
}): Promise<string[]> {
  const q = new URLSearchParams({
    servicio_id: params.servicio_id,
    fecha: params.fecha,
  });
  if (params.empleado_id) q.set("empleado_id", params.empleado_id);
  if (params.sucursal_id) q.set("sucursal_id", params.sucursal_id);
  const r = await pedir<{ slots: string[] }>(api(`/disponibilidad?${q}`));
  return r.slots;
}

export function reservar(datos: DatosReserva) {
  return pedir<{ ok: boolean; mensaje: string }>(api("/reservar"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos),
  });
}

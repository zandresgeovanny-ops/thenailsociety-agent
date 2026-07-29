// Reserva — asistente paso a paso que agenda contra el backend real.
// Flujo: servicio → sucursal → especialista (opcional) → fecha/hora → datos.
// La disponibilidad se pide en vivo; el POST guarda la cita con sucursal_id.

import { forwardRef, useEffect, useMemo, useState } from "react";
import {
  obtenerServicios,
  obtenerSucursales,
  obtenerEmpleados,
  obtenerDisponibilidad,
  reservar,
  type Servicio,
  type Sucursal,
  type Empleado,
} from "../api/reservas";
import BotonMagnetico from "../ui/BotonMagnetico";
import TextoRevelado from "../ui/TextoRevelado";
import "./Reserva.css";

interface Props {
  servicioSugeridoId: string | null;
}

const PASOS = ["Servicio", "Sucursal", "Especialista", "Fecha y hora", "Tus datos"];

const hoyISO = () => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
};

const pesos = (n: number | null) =>
  n == null ? "" : `$${n.toLocaleString("es-MX")}`;

const Reserva = forwardRef<HTMLElement, Props>(function Reserva(
  { servicioSugeridoId },
  ref,
) {
  const [paso, setPaso] = useState(0);
  const [servicios, setServicios] = useState<Servicio[]>([]);
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [empleados, setEmpleados] = useState<Empleado[]>([]);

  const [servicioId, setServicioId] = useState<string | null>(null);
  const [sucursalId, setSucursalId] = useState<string | null>(null);
  const [empleadoId, setEmpleadoId] = useState<string | null>(null); // null = sin preferencia
  const [fecha, setFecha] = useState(hoyISO());
  const [hora, setHora] = useState<string | null>(null);
  const [slots, setSlots] = useState<string[] | null>(null);

  const [nombre, setNombre] = useState("");
  const [telefono, setTelefono] = useState("");

  const [busqueda, setBusqueda] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<string | null>(null);

  // Cargar catálogos base
  useEffect(() => {
    obtenerServicios().then(setServicios).catch(() => {});
    obtenerSucursales().then(setSucursales).catch(() => {});
    obtenerEmpleados().then(setEmpleados).catch(() => {});
  }, []);

  // Preselección de servicio desde otra sección (Servicios / Configurador)
  useEffect(() => {
    if (servicioSugeridoId) {
      setServicioId(servicioSugeridoId);
      setPaso(1);
    }
  }, [servicioSugeridoId]);

  /**
   * Normaliza para buscar: minúsculas y sin acentos. Así "podologia" encuentra
   * "Podología" y "acrilico" encuentra "Acrílico" — nadie escribe los acentos
   * en un buscador desde el teléfono.
   */
  const normalizar = (t: string) =>
    t.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

  /**
   * Filtra por NOMBRE y por CATEGORÍA a la vez: escribir "spa" saca todos los
   * masajes y faciales aunque ninguno tenga "spa" en el nombre. Se admiten
   * varias palabras sueltas ("gel pies") y todas deben aparecer.
   */
  const serviciosFiltrados = useMemo(() => {
    const terminos = normalizar(busqueda).split(/\s+/).filter(Boolean);
    if (terminos.length === 0) return servicios;
    return servicios.filter((s) => {
      const heno = normalizar(`${s.nombre} ${s.categoria}`);
      return terminos.every((t) => heno.includes(t));
    });
  }, [servicios, busqueda]);

  const servicio = useMemo(
    () => servicios.find((s) => s.id === servicioId) ?? null,
    [servicios, servicioId],
  );
  const sucursal = useMemo(
    () => sucursales.find((s) => s.id === sucursalId) ?? null,
    [sucursales, sucursalId],
  );
  const especialistasSucursal = useMemo(
    () => empleados.filter((e) => !sucursalId || e.sucursal_id === sucursalId),
    [empleados, sucursalId],
  );

  // Pedir disponibilidad al entrar al paso de fecha/hora o cambiar sus insumos
  useEffect(() => {
    if (paso !== 3 || !servicioId) return;
    setSlots(null);
    setHora(null);
    obtenerDisponibilidad({
      servicio_id: servicioId,
      fecha,
      empleado_id: empleadoId,
      sucursal_id: empleadoId ? null : sucursalId,
    })
      .then(setSlots)
      .catch(() => setSlots([]));
  }, [paso, servicioId, fecha, empleadoId, sucursalId]);

  const puedeAvanzar =
    (paso === 0 && servicioId) ||
    (paso === 1 && sucursalId) ||
    paso === 2 || // especialista es opcional
    (paso === 3 && hora) ||
    (paso === 4 && nombre.trim() && telefono.trim());

  const enviar = async () => {
    if (!servicioId || !fecha || !hora) return;
    setEnviando(true);
    setError(null);
    try {
      const r = await reservar({
        nombre: nombre.trim(),
        telefono: telefono.trim(),
        servicio_id: servicioId,
        sucursal_id: sucursalId,
        empleado_id: empleadoId,
        fecha,
        hora,
      });
      setExito(r.mensaje);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <section className="reserva" id="reserva" ref={ref}>
      <div className="contenedor reserva__inner">
        <div className="reserva__cabecera">
          <TextoRevelado como="span" className="kicker">
            Agenda tu visita
          </TextoRevelado>
          <TextoRevelado como="h2" className="reserva__titulo" retraso={0.06}>
            Reserva en un minuto
          </TextoRevelado>
        </div>

        {exito ? (
          <div className="reserva__exito">
            <div className="reserva__check" aria-hidden="true">
              ✓
            </div>
            <h3>¡Cita confirmada!</h3>
            <p>{exito}</p>
            <p className="reserva__exito-sub">
              Te enviaremos los detalles por WhatsApp. ¡Te esperamos en The Nail Society Spa!
            </p>
          </div>
        ) : (
          <div className="reserva__tarjeta">
            {/* Progreso */}
            <ol className="reserva__pasos">
              {PASOS.map((p, i) => (
                <li
                  key={p}
                  className={`reserva__paso ${i === paso ? "on" : ""} ${
                    i < paso ? "hecho" : ""
                  }`}
                >
                  <span className="reserva__num">{i < paso ? "✓" : i + 1}</span>
                  <span className="reserva__paso-txt">{p}</span>
                </li>
              ))}
            </ol>

            <div className="reserva__panel">
              {/* Paso 0 — servicio */}
              {paso === 0 && (
                <>
                  {/* Buscador: por nombre y por categoría. Con 37 servicios,
                      hacer scroll es lo que más abandona la reserva. */}
                  <div className="buscador">
                    <span className="buscador__lupa" aria-hidden="true">
                      <svg viewBox="0 0 20 20" width="17" height="17">
                        <circle
                          cx="8.5"
                          cy="8.5"
                          r="5.6"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.7"
                        />
                        <path
                          d="M12.8 12.8L17 17"
                          stroke="currentColor"
                          strokeWidth="1.7"
                          strokeLinecap="round"
                        />
                      </svg>
                    </span>
                    <input
                      type="search"
                      className="buscador__campo"
                      value={busqueda}
                      onChange={(e) => setBusqueda(e.target.value)}
                      placeholder="Busca un servicio o una categoría…"
                      aria-label="Buscar servicio"
                    />
                    {busqueda && (
                      <button
                        className="buscador__limpiar"
                        onClick={() => setBusqueda("")}
                        aria-label="Limpiar búsqueda"
                      >
                        ×
                      </button>
                    )}
                  </div>

                  {/* Atajos por categoría: quien no sabe qué escribir, toca. */}
                  <div className="buscador__atajos">
                    {[...new Set(servicios.map((s) => s.categoria))].map((c) => (
                      <button
                        key={c}
                        className={`atajo ${normalizar(busqueda) === normalizar(c) ? "es-activo" : ""}`}
                        onClick={() =>
                          setBusqueda(normalizar(busqueda) === normalizar(c) ? "" : c)
                        }
                      >
                        {c}
                      </button>
                    ))}
                  </div>

                  <div className="reserva__opciones">
                    {serviciosFiltrados.map((s) => (
                      <button
                        key={s.id}
                        className={`opcion ${servicioId === s.id ? "opcion--on" : ""}`}
                        onClick={() => setServicioId(s.id)}
                      >
                        <span className="opcion__info">
                          <span className="opcion__nombre">{s.nombre}</span>
                          <span className="opcion__meta">
                            {s.categoria} · {s.duracion_min} min
                          </span>
                        </span>
                        <span className="opcion__precio">{pesos(s.precio)}</span>
                      </button>
                    ))}

                    {servicios.length === 0 && (
                      <p className="reserva__vacio">Cargando servicios…</p>
                    )}
                    {servicios.length > 0 && serviciosFiltrados.length === 0 && (
                      <p className="reserva__vacio">
                        No encontramos “{busqueda}”. Prueba con otra palabra, o
                        escríbenos por WhatsApp y te ayudamos.
                      </p>
                    )}
                  </div>
                </>
              )}

              {/* Paso 1 — sucursal */}
              {paso === 1 && (
                <div className="reserva__opciones">
                  {sucursales.map((s) => (
                    <button
                      key={s.id}
                      className={`opcion ${sucursalId === s.id ? "opcion--on" : ""}`}
                      onClick={() => {
                        setSucursalId(s.id);
                        setEmpleadoId(null); // reinicia especialista al cambiar de sede
                      }}
                    >
                      <span className="opcion__info">
                        <span className="opcion__nombre">Sucursal {s.nombre}</span>
                        <span className="opcion__meta">{s.direccion}</span>
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* Paso 2 — especialista (opcional) */}
              {paso === 2 && (
                <div className="reserva__opciones">
                  <button
                    className={`opcion ${empleadoId === null ? "opcion--on" : ""}`}
                    onClick={() => setEmpleadoId(null)}
                  >
                    <span className="opcion__info">
                      <span className="opcion__nombre">Sin preferencia</span>
                      <span className="opcion__meta">
                        Te asignamos a la especialista disponible
                      </span>
                    </span>
                  </button>
                  {especialistasSucursal.map((e) => (
                    <button
                      key={e.id}
                      className={`opcion ${empleadoId === e.id ? "opcion--on" : ""}`}
                      onClick={() => setEmpleadoId(e.id)}
                    >
                      <span className="opcion__info">
                        <span className="opcion__nombre">{e.nombre}</span>
                        {e.especialidad && (
                          <span className="opcion__meta">{e.especialidad}</span>
                        )}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* Paso 3 — fecha y hora */}
              {paso === 3 && (
                <div className="reserva__fecha">
                  <label className="reserva__label">
                    Fecha
                    <input
                      type="date"
                      value={fecha}
                      min={hoyISO()}
                      onChange={(e) => setFecha(e.target.value)}
                    />
                  </label>
                  <div className="reserva__slots-cont">
                    <span className="reserva__label">Horario disponible</span>
                    {slots === null && <p className="reserva__vacio">Buscando huecos…</p>}
                    {slots && slots.length === 0 && (
                      <p className="reserva__vacio">
                        No hay horarios ese día. Prueba con otra fecha.
                      </p>
                    )}
                    {slots && slots.length > 0 && (
                      <div className="reserva__slots">
                        {slots.map((s) => (
                          <button
                            key={s}
                            className={`slot ${hora === s ? "slot--on" : ""}`}
                            onClick={() => setHora(s)}
                          >
                            {s}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Paso 4 — datos */}
              {paso === 4 && (
                <div className="reserva__datos">
                  <div className="reserva__resumen">
                    <span>
                      <b>Servicio</b> {servicio?.nombre}
                    </span>
                    <span>
                      <b>Sucursal</b> {sucursal?.nombre}
                    </span>
                    <span>
                      <b>Fecha</b> {fecha} · {hora}
                    </span>
                  </div>
                  <label className="reserva__label">
                    Tu nombre
                    <input
                      type="text"
                      value={nombre}
                      placeholder="Ej. Andrea Ruiz"
                      onChange={(e) => setNombre(e.target.value)}
                    />
                  </label>
                  <label className="reserva__label">
                    WhatsApp
                    <input
                      type="tel"
                      value={telefono}
                      placeholder="Ej. 449 123 4567"
                      onChange={(e) => setTelefono(e.target.value)}
                    />
                  </label>
                </div>
              )}

              {error && <p className="reserva__error">{error}</p>}
            </div>

            {/* Navegación */}
            <div className="reserva__nav">
              {paso > 0 && (
                <button
                  className="reserva__atras"
                  onClick={() => setPaso((p) => p - 1)}
                  disabled={enviando}
                >
                  ← Atrás
                </button>
              )}
              {paso < 4 ? (
                <BotonMagnetico
                  onClick={() => setPaso((p) => p + 1)}
                  disabled={!puedeAvanzar}
                  className="reserva__siguiente"
                >
                  Continuar
                </BotonMagnetico>
              ) : (
                <BotonMagnetico
                  onClick={enviar}
                  disabled={!puedeAvanzar || enviando}
                  className="reserva__siguiente"
                >
                  {enviando ? "Confirmando…" : "Confirmar cita"}
                </BotonMagnetico>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
});

export default Reserva;

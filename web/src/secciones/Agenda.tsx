// Agenda — disponibilidad real, visible antes de reservar.
//
// Por qué existe: el formulario de reserva obliga a elegir servicio, luego
// fecha, y solo entonces enseña horas. Quien solo quiere saber "¿tienen lugar
// el sábado?" abandona antes de llegar. Esta sección contesta esa pregunta de
// un vistazo, con datos reales del backend.
//
// La disponibilidad depende de la duración del servicio, así que se pide un
// servicio (arranca en el más popular) y se consultan 7 días en paralelo.

import { useEffect, useMemo, useState } from "react";
import {
  obtenerDisponibilidad,
  obtenerServicios,
  obtenerSucursales,
  type Servicio,
  type Sucursal,
} from "../api/reservas";
import TextoRevelado from "../ui/TextoRevelado";
import "./Agenda.css";

const DIAS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const DIAS_A_MOSTRAR = 7;

/** Fecha en YYYY-MM-DD respetando la zona local (toISOString la desplazaría). */
const aISO = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

interface Props {
  alReservarServicio: (servicioId: string) => void;
}

export default function Agenda({ alReservarServicio }: Props) {
  const [servicios, setServicios] = useState<Servicio[]>([]);
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [servicioId, setServicioId] = useState<string>("");
  const [sucursalId, setSucursalId] = useState<string>("");
  const [porDia, setPorDia] = useState<Record<string, string[]>>({});
  const [diaActivo, setDiaActivo] = useState<string>("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);

  // Los próximos 7 días a partir de hoy.
  const dias = useMemo(() => {
    const hoy = new Date();
    return Array.from({ length: DIAS_A_MOSTRAR }, (_, i) => {
      const d = new Date(hoy);
      d.setDate(hoy.getDate() + i);
      return d;
    });
  }, []);

  // Catálogo y sucursales, una sola vez.
  useEffect(() => {
    Promise.all([obtenerServicios(), obtenerSucursales()])
      .then(([servs, sucs]) => {
        setServicios(servs);
        setSucursales(sucs);
        // Arranca en un servicio corto y frecuente: es el que más hueco tiene
        // y evita que la primera impresión sea una agenda vacía.
        const arranque =
          servs.find((s) => s.nombre.toLowerCase().includes("esmaltado en gel")) ?? servs[0];
        if (arranque) setServicioId(arranque.id);
      })
      .catch(() => setError(true));
  }, []);

  // Disponibilidad de los 7 días, en paralelo. Se relanza al cambiar
  // servicio o sucursal.
  useEffect(() => {
    if (!servicioId) return;
    let vigente = true;
    setCargando(true);

    Promise.all(
      dias.map((d) =>
        obtenerDisponibilidad({
          servicio_id: servicioId,
          fecha: aISO(d),
          sucursal_id: sucursalId || null,
        })
          .then((slots) => [aISO(d), slots] as const)
          .catch(() => [aISO(d), [] as string[]] as const),
      ),
    ).then((pares) => {
      if (!vigente) return;
      const mapa = Object.fromEntries(pares);
      setPorDia(mapa);
      // Se abre en el primer día que tenga hueco, no en uno vacío.
      const primero = dias.map(aISO).find((f) => (mapa[f] ?? []).length > 0);
      setDiaActivo(primero ?? aISO(dias[0]));
      setCargando(false);
    });

    return () => {
      vigente = false;
    };
  }, [servicioId, sucursalId, dias]);

  const servicio = servicios.find((s) => s.id === servicioId);
  const slots = porDia[diaActivo] ?? [];

  if (error) return null;

  return (
    <section className="agenda seccion-oscura" id="agenda">
      <div className="contenedor">
        <div className="agenda__cabecera">
          <TextoRevelado como="span" className="agenda__kicker">
            Disponibilidad en vivo
          </TextoRevelado>
          <TextoRevelado como="h2" className="agenda__titulo" retraso={0.06}>
            ¿Cuándo te <em>acomoda</em>?
          </TextoRevelado>
          <TextoRevelado como="p" className="agenda__entrada" retraso={0.12}>
            Estos son los lugares que quedan esta semana. Elige uno y te llevamos
            directo a la reserva.
          </TextoRevelado>
        </div>

        {/* Filtros: servicio y sucursal */}
        <div className="agenda__filtros">
          <label className="agenda__campo">
            <span>Servicio</span>
            <select value={servicioId} onChange={(e) => setServicioId(e.target.value)}>
              {servicios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nombre} · {s.duracion_min} min
                </option>
              ))}
            </select>
          </label>

          <div className="agenda__sucursales" role="group" aria-label="Sucursal">
            <button
              className={`agenda__suc ${sucursalId === "" ? "es-activo" : ""}`}
              onClick={() => setSucursalId("")}
            >
              Cualquiera
            </button>
            {sucursales.map((s) => (
              <button
                key={s.id}
                className={`agenda__suc ${sucursalId === s.id ? "es-activo" : ""}`}
                onClick={() => setSucursalId(s.id)}
              >
                {s.nombre}
              </button>
            ))}
          </div>
        </div>

        {/* Tira de días: cada uno muestra cuántos lugares quedan */}
        <div className="agenda__dias">
          {dias.map((d, i) => {
            const iso = aISO(d);
            const libres = (porDia[iso] ?? []).length;
            const vacio = !cargando && libres === 0;
            return (
              <button
                key={iso}
                className={`dia ${diaActivo === iso ? "es-activo" : ""} ${vacio ? "es-vacio" : ""}`}
                onClick={() => setDiaActivo(iso)}
                disabled={vacio}
              >
                <span className="dia__nombre">{i === 0 ? "Hoy" : DIAS[d.getDay()]}</span>
                <span className="dia__num">{d.getDate()}</span>
                <span className="dia__mes">{MESES[d.getMonth()]}</span>
                <span className="dia__libres">
                  {cargando ? "···" : vacio ? "lleno" : `${libres} lugares`}
                </span>
              </button>
            );
          })}
        </div>

        {/* Horas del día activo */}
        <div className="agenda__horas">
          {cargando && (
            <div className="agenda__skel">
              {Array.from({ length: 10 }).map((_, i) => (
                <span key={i} />
              ))}
            </div>
          )}

          {!cargando && slots.length === 0 && (
            <p className="agenda__vacio">
              No queda lugar ese día para {servicio?.nombre ?? "este servicio"}. Prueba
              otra fecha o la otra sucursal.
            </p>
          )}

          {!cargando && slots.length > 0 && (
            <>
              <div className="agenda__rejilla">
                {slots.map((h) => (
                  <button
                    key={h}
                    className="hora"
                    onClick={() => alReservarServicio(servicioId)}
                    title={`Reservar ${servicio?.nombre ?? ""} a las ${h}`}
                  >
                    {h}
                  </button>
                ))}
              </div>
              <p className="agenda__nota">
                Horarios reales, actualizados al momento. Al elegir uno pasas a la
                reserva con el servicio ya seleccionado.
              </p>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

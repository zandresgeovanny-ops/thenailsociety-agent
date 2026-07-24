// Equipo — las especialistas reales del salón, traídas del backend. Avatar
// tipográfico con inicial sobre filete dorado, nombre y especialidad.

import { useEffect, useState } from "react";
import { obtenerEmpleados, type Empleado } from "../api/reservas";
import TarjetaTilt from "../ui/TarjetaTilt";
import TextoRevelado from "../ui/TextoRevelado";
import "./Equipo.css";

const inicial = (n: string) => n.trim().charAt(0).toUpperCase();

export default function Equipo() {
  const [equipo, setEquipo] = useState<Empleado[] | null>(null);

  useEffect(() => {
    obtenerEmpleados()
      .then(setEquipo)
      .catch(() => setEquipo([]));
  }, []);

  if (equipo && equipo.length === 0) return null;

  return (
    <section className="equipo seccion-oscura" id="equipo">
      <div className="contenedor">
        <div className="equipo__cabecera">
          <TextoRevelado como="span" className="kicker">
            Manos expertas
          </TextoRevelado>
          <TextoRevelado como="h2" className="equipo__titulo" retraso={0.06}>
            Conoce a nuestro equipo
          </TextoRevelado>
        </div>

        <div className="equipo__grid">
          {(equipo ?? Array.from({ length: 4 }).map(() => null)).map((e, i) =>
            e ? (
              <TarjetaTilt key={e.id} className="miembro" intensidad={6}>
                <div className="miembro__cuerpo">
                  <span className="miembro__avatar">{inicial(e.nombre)}</span>
                  <h3 className="miembro__nombre">{e.nombre}</h3>
                  <p className="miembro__esp">{e.especialidad ?? "Spa & belleza"}</p>
                </div>
              </TarjetaTilt>
            ) : (
              <div key={i} className="miembro-skel" />
            ),
          )}
        </div>
      </div>
    </section>
  );
}

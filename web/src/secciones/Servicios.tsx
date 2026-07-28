// Servicios — catálogo real traído del backend, agrupado por categoría.
// Cada servicio es una TarjetaTilt con nombre, duración y precio. El precio se
// muestra en tinta (nunca en dorado) y con el bronce como acento del "desde".

import { useEffect, useState } from "react";
import { obtenerServicios, type Servicio } from "../api/reservas";
import TarjetaTilt from "../ui/TarjetaTilt";
import TextoRevelado from "../ui/TextoRevelado";
import "./Servicios.css";

interface Props {
  alReservarServicio: (servicioId: string) => void;
}

function agrupar(servicios: Servicio[]): Record<string, Servicio[]> {
  return servicios.reduce<Record<string, Servicio[]>>((acc, s) => {
    (acc[s.categoria] ||= []).push(s);
    return acc;
  }, {});
}

const pesos = (n: number | null) =>
  n == null ? "Consultar" : `$${n.toLocaleString("es-MX")}`;

export default function Servicios({ alReservarServicio }: Props) {
  const [servicios, setServicios] = useState<Servicio[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    obtenerServicios()
      .then(setServicios)
      .catch((e) => setError(e.message));
  }, []);

  const grupos = servicios ? agrupar(servicios) : {};

  return (
    <section className="servicios" id="servicios">
      <div className="contenedor">
        <div className="servicios__cabecera">
          <TextoRevelado como="span" className="kicker">
            Carta de servicios
          </TextoRevelado>
          <TextoRevelado como="h2" className="servicios__titulo" retraso={0.06}>
            Todo lo que tus manos merecen
          </TextoRevelado>
        </div>

        {error && (
          <p className="servicios__aviso">
            No pudimos cargar el catálogo ahora mismo. Escríbenos por WhatsApp y con
            gusto te lo compartimos.
          </p>
        )}

        {!servicios && !error && (
          <div className="servicios__grid">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="servicio-skel" />
            ))}
          </div>
        )}

        {servicios &&
          Object.entries(grupos).map(([categoria, items]) => (
            <div key={categoria} className="servicios__categoria">
              <h3 className="servicios__catnombre">{categoria}</h3>
              <div className="servicios__grid">
                {items.map((s) => (
                  <TarjetaTilt key={s.id} className="servicio">
                    <div className="servicio__cuerpo">
                      <div className="servicio__top">
                        <h4 className="servicio__nombre">{s.nombre}</h4>
                        <span className="servicio__dur">{s.duracion_min} min</span>
                      </div>
                      <div className="servicio__pie">
                        <span className="servicio__precio">
                          <em>desde</em> {pesos(s.precio)}
                        </span>
                        <button
                          className="servicio__reservar"
                          onClick={() => alReservarServicio(s.id)}
                        >
                          Reservar →
                        </button>
                      </div>
                    </div>
                  </TarjetaTilt>
                ))}
              </div>
            </div>
          ))}
      </div>
    </section>
  );
}

// Configurador — sección estrella. A la izquierda, la mano 3D con las uñas
// pintadas en vivo; a la derecha, los selectores de color y acabado. El look
// elegido se puede llevar directo a la reserva.

import ConfiguradorUnas from "../escena/ConfiguradorUnas";
import TextoRevelado from "../ui/TextoRevelado";
import BotonMagnetico from "../ui/BotonMagnetico";
import { ACABADOS, COLORES, type EstadoConfig } from "../escena/materiales";
import "./Configurador.css";

interface Props {
  config: EstadoConfig;
  setConfig: (c: EstadoConfig) => void;
  alReservar: () => void;
}

export default function Configurador({ config, setConfig, alReservar }: Props) {
  return (
    <section className="config seccion-oscura" id="configurador">
      <div className="config__inner contenedor">
        <div className="config__intro">
          <TextoRevelado como="span" className="kicker">
            Estudio de diseño
          </TextoRevelado>
          <TextoRevelado como="h2" className="config__titulo" retraso={0.06}>
            Diseña tus uñas en 3D
          </TextoRevelado>
          <TextoRevelado como="p" className="config__desc" retraso={0.12}>
            Gira la mano, prueba colores y acabados con reflejos reales. Cuando te
            enamores de un look, llévalo a tu reserva con un clic.
          </TextoRevelado>
        </div>

        <div className="config__grid">
          {/* Lienzo 3D */}
          <div className="config__lienzo">
            <ConfiguradorUnas config={config} />
            <span className="config__pista" aria-hidden="true">
              Arrastra para girar
            </span>
          </div>

          {/* Controles */}
          <div className="config__panel">
            <fieldset className="config__campo">
              <legend>Color de esmalte</legend>
              <div className="config__colores">
                {COLORES.map((c) => {
                  const activo = c.hex === config.color.hex;
                  return (
                    <button
                      key={c.hex}
                      className={`swatch ${activo ? "swatch--on" : ""}`}
                      style={{ background: c.hex }}
                      onClick={() => setConfig({ ...config, color: c })}
                      aria-pressed={activo}
                      aria-label={c.nombre}
                      title={c.nombre}
                    />
                  );
                })}
              </div>
              <p className="config__valor">{config.color.nombre}</p>
            </fieldset>

            <fieldset className="config__campo">
              <legend>Acabado</legend>
              <div className="config__acabados">
                {ACABADOS.map((a) => {
                  const activo = a.clave === config.acabado.clave;
                  return (
                    <button
                      key={a.clave}
                      className={`chip ${activo ? "chip--on" : ""}`}
                      onClick={() => setConfig({ ...config, acabado: a })}
                      aria-pressed={activo}
                    >
                      {a.nombre}
                    </button>
                  );
                })}
              </div>
            </fieldset>

            <BotonMagnetico onClick={alReservar} className="config__reservar">
              Reservar este look
            </BotonMagnetico>
          </div>
        </div>
      </div>
    </section>
  );
}

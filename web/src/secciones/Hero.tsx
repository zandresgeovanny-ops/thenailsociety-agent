// Hero — primera impresión. Fondo negro estructural con auroras doradas.
// Titular serif grande, filete dorado, y dos llamadas: reservar (naranja) y
// diseñar tus uñas (contorno dorado).

import BotonMagnetico from "../ui/BotonMagnetico";
import TextoRevelado from "../ui/TextoRevelado";
import FondoAurora from "../ui/FondoAurora";
import "./Hero.css";

interface Props {
  alReservar: () => void;
  alConfigurar: () => void;
}

export default function Hero({ alReservar, alConfigurar }: Props) {
  return (
    <section className="hero seccion-oscura" id="top">
      <FondoAurora variante="oscuro" />
      <div className="hero__contenido contenedor">
        <TextoRevelado como="span" className="kicker hero__kicker">
          Uñas · Spa · Belleza de autor
        </TextoRevelado>
        <TextoRevelado como="h1" className="hero__titulo" retraso={0.08}>
          Tu manicura,
          <br />
          diseñada como <em>arte</em>.
        </TextoRevelado>
        <TextoRevelado como="p" className="hero__sub" retraso={0.16}>
          En The Nail Society Spa cada cita es una experiencia. Diseña tu look en 3D,
          elígelo a tu gusto y resérvalo en segundos — en nuestras sucursales Norte y Sur
          de Aguascalientes.
        </TextoRevelado>
        <TextoRevelado className="hero__acciones" retraso={0.24}>
          <BotonMagnetico onClick={alReservar}>Reservar mi cita</BotonMagnetico>
          <BotonMagnetico variante="contorno" onClick={alConfigurar}>
            Diseñar mis uñas
          </BotonMagnetico>
        </TextoRevelado>
      </div>
      <div className="hero__filete" aria-hidden="true" />
    </section>
  );
}

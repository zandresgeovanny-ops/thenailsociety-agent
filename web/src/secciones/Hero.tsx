// Hero — primera impresión, estilo editorial de alta costura.
// Rejilla asimétrica (CSS Grid): el texto vive a la izquierda, alineado a la
// izquierda (nunca centrado). La mitad derecha la ocupa una escena 3D posicionada
// de forma absoluta: un contenedor VACÍO (#hero-canvas-3d) listo para incrustar
// el <canvas> de Three.js con la mano cuyas uñas se revelan al hacer scroll.

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
    <section className="hero" id="top">
      <FondoAurora variante="claro" />

      {/* Recursos de revista: etiqueta vertical al borde y número índice de fondo */}
      <span className="hero__vertical" aria-hidden="true">
        Norte &middot; Sur — Aguascalientes
      </span>
      <span className="hero__indice" aria-hidden="true">01</span>

      {/* Rejilla asimétrica: columna de texto ancha a la izquierda, aire a la derecha */}
      <div className="hero__grid contenedor">
        <div className="hero__texto">
          <TextoRevelado como="span" className="hero__kicker">
            <span className="hero__regla" aria-hidden="true" />
            Nail Society — belleza de autor
          </TextoRevelado>

          <TextoRevelado como="h1" className="hero__titulo" retraso={0.08}>
            La manicura
            <br />
            como <em>alta costura</em>.
          </TextoRevelado>

          <TextoRevelado como="p" className="hero__sub" retraso={0.16}>
            Diseña tu look en 3D, elígelo a tu gusto y resérvalo en segundos.
            Un spa donde cada uña es una pieza única, en nuestras sucursales
            Norte y Sur.
          </TextoRevelado>

          <TextoRevelado className="hero__acciones" retraso={0.24}>
            <BotonMagnetico onClick={alReservar}>Reservar mi cita</BotonMagnetico>
            <BotonMagnetico variante="contorno" onClick={alConfigurar}>
              Diseñar mis uñas
            </BotonMagnetico>
          </TextoRevelado>

          <TextoRevelado className="hero__meta" retraso={0.32}>
            <span>
              <b>02</b> sucursales
            </span>
            <span>
              <b>Est.</b> Aguascalientes
            </span>
            <a
              className="hero__ig"
              href="https://instagram.com/thenailsociety_ags"
              target="_blank"
              rel="noreferrer"
            >
              @thenailsociety_ags
            </a>
          </TextoRevelado>
        </div>
      </div>

      {/*
        Escenario 3D — contenedor VACÍO posicionado en el lado derecho.
        Aquí se monta el <canvas> de Three.js (mano + uñas). El marco dorado y el
        fondo de estudio están pensados para que la mano resalte; el <canvas> se
        dibuja encima y tapa el placeholder cuando llegue el modelo.
      */}
      <div className="hero__escena" id="hero-canvas-3d">
        <div className="hero__escena-marco" aria-hidden="true">
          <span className="hero__escena-hint">Tu diseño, en 3D</span>
        </div>
      </div>

      {/* Indicador de scroll, alineado a la izquierda */}
      <div className="hero__scroll" aria-hidden="true">
        <span>Desliza</span>
        <i />
      </div>
    </section>
  );
}

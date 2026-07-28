// Hero — primera impresión, estilo editorial de alta costura.
// Dos bloques dentro de una rejilla CSS: a la izquierda el TEXTO, a la derecha
// el MODELO 3D (la mano). Al hacer scroll se produce un "intercambio de
// posiciones": el modelo se desplaza en X hacia la izquierda PASANDO POR DETRÁS
// del texto (menor z-index), mientras el texto se desplaza a la derecha por
// encima. Sincronizado al scroll con GSAP ScrollTrigger (scrub).

import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import BotonMagnetico from "../ui/BotonMagnetico";
import TextoRevelado from "../ui/TextoRevelado";
import FondoAurora from "../ui/FondoAurora";
import ManoHero from "../escena/ManoHero";
import { prefiereMenosMovimiento } from "../lib/preferencias";
import "./Hero.css";

gsap.registerPlugin(ScrollTrigger, useGSAP);

interface Props {
  alReservar: () => void;
  alVerServicios: () => void;
}

export default function Hero({ alReservar, alVerServicios }: Props) {
  const seccion = useRef<HTMLElement>(null);
  const bloqueTexto = useRef<HTMLDivElement>(null);
  const bloqueModelo = useRef<HTMLDivElement>(null);

  // Intercambio de posiciones al hacer scroll por el hero. scrub: true → sigue
  // el desplazamiento del usuario de forma continua. Se omite si pidió menos
  // movimiento o en pantallas apiladas (móvil), donde el swap en X no aplica.
  useGSAP(
    () => {
      // Respetar accesibilidad: sin animación si el sistema pide menos movimiento.
      if (prefiereMenosMovimiento()) return;

      // matchMedia gatea por ancho y limpia solo al cambiar de rango (o al
      // desmontar). El swap en X solo tiene sentido en escritorio (>=981px);
      // en móvil el CSS apila y anula transform con !important.
      const mm = gsap.matchMedia();
      mm.add("(min-width: 981px)", () => {
        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: seccion.current,
            start: "top top",
            // Rango FIJO de una pantalla de scroll. No depende de medir el alto
            // de la sección (que aún es 0 cuando el Canvas 3D no ha asentado el
            // layout) — así el swap tiene rango válido desde el primer frame.
            end: "+=100%",
            scrub: true,
            invalidateOnRefresh: true,
          },
        });
        // Texto se va a la derecha (queda por encima); modelo a la izquierda
        // pasando por detrás (menor z-index en el CSS).
        tl.to(bloqueTexto.current, { xPercent: 62, ease: "none" }, 0).to(
          bloqueModelo.current,
          { xPercent: -88, ease: "none" },
          0,
        );
      });

      // El Canvas 3D y las fuentes montan async y cambian el layout después de
      // que ScrollTrigger midió: re-medimos una vez tras el load para afinar
      // la posición de arranque (start).
      const refrescar = () => ScrollTrigger.refresh();
      window.addEventListener("load", refrescar);
      return () => window.removeEventListener("load", refrescar);
    },
    { scope: seccion },
  );

  return (
    <section className="hero" id="top" ref={seccion}>
      <FondoAurora variante="claro" />

      {/* Recursos de revista: etiqueta vertical al borde y número índice de fondo */}
      <span className="hero__vertical" aria-hidden="true">
        Norte &middot; Sur — Aguascalientes
      </span>
      <span className="hero__indice" aria-hidden="true">01</span>

      <div className="hero__grid contenedor">
        {/* ── Bloque IZQUIERDO: texto (siempre por encima en el swap) ── */}
        <div className="hero__bloque hero__bloque--texto" ref={bloqueTexto}>
          {/* Todo el copy de aquí abajo sale del vocabulario real de la marca
              (knowledge/thenailsociety_brand_voice.md): "sofisticado",
              "consentirte como mereces", "un momento para ti", "agenda tu
              cita". Nada inventado. */}
          <TextoRevelado como="span" className="hero__kicker">
            <span className="hero__regla" aria-hidden="true" />
            Nail spa · Aguascalientes
          </TextoRevelado>

          <TextoRevelado como="h1" className="hero__titulo" retraso={0.08}>
            Relájate y consiéntete
            <br />
            como <em>mereces</em>.
          </TextoRevelado>

          <TextoRevelado como="p" className="hero__sub" retraso={0.16}>
            Uñas, spa, faciales y podología en el lugar más sofisticado de
            Aguascalientes. Dos sucursales, Norte y Sur, y 37 servicios para
            darte un momento para ti.
          </TextoRevelado>

          <TextoRevelado className="hero__acciones" retraso={0.24}>
            <BotonMagnetico onClick={alReservar}>Agendar mi cita</BotonMagnetico>
            <BotonMagnetico variante="contorno" onClick={alVerServicios}>
              Ver la carta
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

        {/* ── Bloque DERECHO: modelo 3D (pasa por detrás en el swap) ── */}
        <div className="hero__bloque hero__bloque--modelo" ref={bloqueModelo}>
          <div className="hero__escena-marco">
            <ManoHero />
            <span className="hero__escena-hint">Modelo: deep3dstudio · CC-BY-NC</span>
          </div>
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

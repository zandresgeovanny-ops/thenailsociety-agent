// Hero — "Sello". Primera impresión en negro, con marco dorado y el titular
// centrado en itálica serif. Sin fotografía y sin 3D: el peso lo llevan la
// tipografía y el vacío, que es exactamente el registro "quiet luxury" que
// describe la guía de marca.
//
// Decisión de diseño: se retiró el modelo 3D del hero. Competía con el
// titular y obligaba a cargar 1.3 MB antes de que se leyera una sola palabra.
//
// Todo el copy sale del vocabulario real de la marca
// (knowledge/thenailsociety_brand_voice.md). Las cifras de reseñas vienen de
// datos/resenas.ts, que a su vez sale del CSV de Google.

import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import BotonMagnetico from "../ui/BotonMagnetico";
import TextoRevelado from "../ui/TextoRevelado";
import { prefiereMenosMovimiento } from "../lib/preferencias";
import { CALIFICACION_MEDIA, TOTAL_RESENAS } from "../datos/resenas";
import "./Hero.css";

gsap.registerPlugin(ScrollTrigger, useGSAP);

interface Props {
  alReservar: () => void;
  alVerServicios: () => void;
}

export default function Hero({ alReservar, alVerServicios }: Props) {
  const seccion = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      if (prefiereMenosMovimiento()) return;

      // Al bajar, el contenido se aleja y se desvanece: da la sensación de que
      // el sello se queda atrás en vez de empujar la página hacia arriba.
      gsap.to(".hero__inner", {
        y: -70,
        opacity: 0,
        scale: 0.97,
        ease: "none",
        scrollTrigger: {
          trigger: seccion.current,
          start: "top top",
          end: "bottom 40%",
          scrub: true,
        },
      });
    },
    { scope: seccion },
  );

  return (
    // `seccion-oscura` no es decorativa: es la que le dice a BotonMagnetico
    // que pinte el botón de contorno en crema. Sin ella el texto sale en
    // tinta sobre negro y desaparece.
    <section className="hero seccion-oscura" id="top" ref={seccion}>
      {/* Capas decorativas: trama de damasco y marco de sello */}
      <div className="hero__trama" aria-hidden="true" />
      <div className="hero__marco" aria-hidden="true" />

      <div className="hero__inner">
        <TextoRevelado className="hero__medalla">
          <span>TNS</span>
        </TextoRevelado>

        <TextoRevelado como="span" className="hero__kicker" retraso={0.06}>
          The Nail Society · Aguascalientes
        </TextoRevelado>

        <TextoRevelado como="h1" className="hero__titulo" retraso={0.12}>
          Relájate y consiéntete
          <em>como mereces</em>
        </TextoRevelado>

        <TextoRevelado className="hero__regla" retraso={0.2}>
          <span />
        </TextoRevelado>

        <TextoRevelado como="p" className="hero__sub" retraso={0.26}>
          Uñas, spa, faciales y podología. Dos sucursales, Norte y Sur, y 37
          servicios para darte un momento para ti.
        </TextoRevelado>

        <TextoRevelado className="hero__acciones" retraso={0.32}>
          <BotonMagnetico onClick={alReservar}>Agendar mi cita</BotonMagnetico>
          <BotonMagnetico variante="contorno" onClick={alVerServicios}>
            Ver el catálogo
          </BotonMagnetico>
        </TextoRevelado>

        <TextoRevelado como="p" className="hero__pie" retraso={0.38}>
          {CALIFICACION_MEDIA.toFixed(1)} en Google · {TOTAL_RESENAS} reseñas
        </TextoRevelado>
      </div>

      <div className="hero__scroll" aria-hidden="true">
        <span>Desliza</span>
        <i />
      </div>
    </section>
  );
}

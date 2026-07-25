// ManoHero — la mano 3D del hero. Incrusta la escena de Spline (publicada por
// el salón como enlace de visor) mediante un <iframe>, y al hacer scroll la
// acerca ligeramente a la pantalla con GSAP ScrollTrigger para que la mano se
// vuelva más protagonista.
//
// La URL se lee de VITE_SPLINE_HERO. Mientras no exista, se muestra un marcador
// elegante de marca (nunca un hueco roto).

import { useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger, useGSAP);

// URL de la escena Spline (enlace de visor my.spline.design). Se puede
// sobrescribir con la env VITE_SPLINE_HERO; si no, usa la escena publicada del
// salón para que producción funcione sin configuración extra.
const ESCENA_POR_DEFECTO =
  "https://my.spline.design/particleshand-om4U3Zzs33VSaC7TbheRtyBR/";
const ESCENA_SPLINE =
  (import.meta.env.VITE_SPLINE_HERO as string | undefined)?.trim() || ESCENA_POR_DEFECTO;

// ¿El usuario pidió menos movimiento? Entonces no animamos el acercamiento.
const reduceMovimiento =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function ManoHero() {
  const cont = useRef<HTMLDivElement>(null);
  const capa = useRef<HTMLDivElement>(null);
  const [cargada, setCargada] = useState(false);

  // Acercamiento al hacer scroll: la mano crece y sube un poco, sincronizada
  // con la barra de desplazamiento. Se salta si el usuario prefiere sin
  // movimiento o si aún no hay escena real que animar.
  useGSAP(
    () => {
      if (reduceMovimiento || !ESCENA_SPLINE || !capa.current) return;
      gsap.fromTo(
        capa.current,
        { scale: 1, yPercent: 0 },
        {
          scale: 1.22,
          yPercent: -6,
          ease: "none",
          scrollTrigger: {
            trigger: "#top",
            start: "top top",
            end: "bottom top",
            scrub: 0.6,
          },
        },
      );
    },
    { scope: cont },
  );

  return (
    <div className="mano-hero" ref={cont}>
      <div className="mano-hero__capa" ref={capa}>
        {ESCENA_SPLINE ? (
          <>
            <iframe
              className="mano-hero__frame"
              src={ESCENA_SPLINE}
              title="Mano 3D — The Nail Society"
              loading="lazy"
              onLoad={() => setCargada(true)}
              allow="autoplay; fullscreen"
            />
            {/* Parche que oculta el sello "Built with Spline" de la esquina */}
            <span className="mano-hero__sello-tapa" aria-hidden="true" />
            {!cargada && <Marcador cargando />}
          </>
        ) : (
          <Marcador />
        )}
      </div>
    </div>
  );
}

// Marcador de marca mientras carga la escena (o mientras no hay URL configurada).
function Marcador({ cargando = false }: { cargando?: boolean }) {
  return (
    <div className="mano-hero__marcador" aria-hidden="true">
      <span className="mano-hero__anillo" />
      <span className="mano-hero__texto">
        {cargando ? "Preparando la escena…" : "Tu diseño, en 3D"}
      </span>
    </div>
  );
}

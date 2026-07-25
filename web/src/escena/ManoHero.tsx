// ManoHero — la mano 3D del hero. Incrusta una escena de Spline (publicada por
// el salón) y, al hacer scroll, la acerca ligeramente a la pantalla con GSAP
// ScrollTrigger para que la mano se vuelva más protagonista.
//
// La URL de la escena se lee de la variable de entorno VITE_SPLINE_HERO. Mientras
// no exista, se muestra un marcador elegante de marca (nunca un hueco roto).

import { Suspense, lazy, useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger, useGSAP);

// Carga diferida: el runtime 3D solo pesa si de verdad hay escena que mostrar.
const Spline = lazy(() => import("@splinetool/react-spline"));

// URL de la escena Spline (scene.splinecode). Vacía hasta que el salón la publique.
const ESCENA_SPLINE = (import.meta.env.VITE_SPLINE_HERO as string | undefined)?.trim();

// ¿El usuario pidió menos movimiento? Entonces no animamos el acercamiento.
const reduceMovimiento =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function ManoHero() {
  const cont = useRef<HTMLDivElement>(null);
  const capa = useRef<HTMLDivElement>(null);

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
          <Suspense fallback={<Marcador cargando />}>
            <Spline scene={ESCENA_SPLINE} />
          </Suspense>
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

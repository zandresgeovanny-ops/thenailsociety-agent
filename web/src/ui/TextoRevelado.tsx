// TextoRevelado — revela su contenido (fundido + desplazamiento) cuando entra
// en pantalla, usando IntersectionObserver. Respeta prefers-reduced-motion.

import { createElement, useEffect, useRef, useState, type ElementType, type ReactNode } from "react";
import { usaMovimientoReducido } from "../lib/preferencias";
import "./TextoRevelado.css";

interface Props {
  children: ReactNode;
  como?: ElementType;
  retraso?: number; // segundos
  className?: string;
}

export default function TextoRevelado({
  children,
  como: Como = "div",
  retraso = 0,
  className = "",
}: Props) {
  const ref = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);
  const reducido = usaMovimientoReducido();

  useEffect(() => {
    if (reducido) {
      setVisible(true);
      return;
    }
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entrada]) => {
        if (entrada.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold: 0.18 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [reducido]);

  return createElement(
    Como,
    {
      ref,
      className: `revelado ${visible ? "revelado--on" : ""} ${className}`,
      style: { transitionDelay: `${retraso}s` },
    },
    children,
  );
}

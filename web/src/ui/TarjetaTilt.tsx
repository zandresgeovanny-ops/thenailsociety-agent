// TarjetaTilt — tarjeta con inclinación 3D según el cursor y un "spotlight"
// dorado que sigue al puntero. Usada para servicios y equipo.
// Con movimiento reducido queda plana y sin spotlight animado.

import { useRef, type ReactNode, type MouseEvent } from "react";
import { usaMovimientoReducido } from "../lib/preferencias";
import "./TarjetaTilt.css";

interface Props {
  children: ReactNode;
  className?: string;
  intensidad?: number; // grados máximos de inclinación
}

export default function TarjetaTilt({ children, className = "", intensidad = 8 }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const reducido = usaMovimientoReducido();

  const mover = (e: MouseEvent) => {
    if (reducido || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width;
    const py = (e.clientY - r.top) / r.height;
    const rx = (0.5 - py) * intensidad;
    const ry = (px - 0.5) * intensidad;
    ref.current.style.transform = `perspective(800px) rotateX(${rx}deg) rotateY(${ry}deg)`;
    ref.current.style.setProperty("--mx", `${px * 100}%`);
    ref.current.style.setProperty("--my", `${py * 100}%`);
  };
  const salir = () => {
    if (ref.current) ref.current.style.transform = "";
  };

  return (
    <div
      ref={ref}
      className={`tarjeta-tilt ${className}`}
      onMouseMove={mover}
      onMouseLeave={salir}
    >
      <span className="tarjeta-tilt__luz" aria-hidden="true" />
      <div className="tarjeta-tilt__cuerpo">{children}</div>
    </div>
  );
}

// BotonMagnetico — el botón sigue sutilmente al cursor cuando está cerca,
// dando sensación de "imán". El CTA principal de la marca, en dorado de acento.
// Con movimiento reducido no se desplaza (queda como botón normal).

import { useRef, type ReactNode, type MouseEvent } from "react";
import { usaMovimientoReducido } from "../lib/preferencias";
import "./BotonMagnetico.css";

interface Props {
  children: ReactNode;
  onClick?: () => void;
  href?: string;
  variante?: "solido" | "contorno";
  type?: "button" | "submit";
  disabled?: boolean;
  className?: string;
}

export default function BotonMagnetico({
  children,
  onClick,
  href,
  variante = "solido",
  type = "button",
  disabled = false,
  className = "",
}: Props) {
  const ref = useRef<HTMLElement>(null);
  const reducido = usaMovimientoReducido();

  const mover = (e: MouseEvent) => {
    if (reducido || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const x = e.clientX - (r.left + r.width / 2);
    const y = e.clientY - (r.top + r.height / 2);
    ref.current.style.transform = `translate(${x * 0.28}px, ${y * 0.4}px)`;
  };
  const salir = () => {
    if (ref.current) ref.current.style.transform = "";
  };

  const clases = `boton-mag boton-mag--${variante} ${className}`;

  if (href) {
    return (
      <a
        ref={ref as React.RefObject<HTMLAnchorElement>}
        className={clases}
        href={href}
        onMouseMove={mover}
        onMouseLeave={salir}
      >
        {children}
      </a>
    );
  }

  return (
    <button
      ref={ref as React.RefObject<HTMLButtonElement>}
      type={type}
      className={clases}
      onClick={onClick}
      onMouseMove={mover}
      onMouseLeave={salir}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

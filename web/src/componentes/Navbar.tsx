// Navbar — barra superior fija. Sobre el hero (negro) va transparente para no
// romper la primera impresión; en cuanto se hace scroll se vuelve sólida y
// clara, que es el fondo del resto de la página.
// El logotipo es tipográfico (serif) con un filete dorado. El CTA de reservar
// es el único botón sólido.

import { useEffect, useState } from "react";
import BotonMagnetico from "../ui/BotonMagnetico";
import "./Navbar.css";

interface Props {
  alReservar: () => void;
}

export default function Navbar({ alReservar }: Props) {
  const [bajado, setBajado] = useState(false);

  useEffect(() => {
    // Umbral generoso: la barra solo se vuelve sólida cuando el hero ya salió
    // de plano, no al primer pixel de scroll.
    const alScroll = () => setBajado(window.scrollY > 80);
    alScroll();
    window.addEventListener("scroll", alScroll, { passive: true });
    return () => window.removeEventListener("scroll", alScroll);
  }, []);

  return (
    <header className={`navbar ${bajado ? "navbar--solida" : "navbar--sobre-hero"}`}>
      <div className="navbar__inner contenedor">
        <a className="navbar__marca" href="#top">
          <span className="navbar__nombre">The Nail Society</span>
          <span className="navbar__spa">SPA · AGUASCALIENTES</span>
        </a>
        <nav className="navbar__links" aria-label="Secciones">
          <a href="#servicios">Servicios</a>
          <a href="#equipo">Equipo</a>
          <a href="#resenas">Reseñas</a>
          <a href="#sucursales">Sucursales</a>
        </nav>
        <BotonMagnetico onClick={alReservar} className="navbar__cta">
          Agendar
        </BotonMagnetico>
      </div>
    </header>
  );
}

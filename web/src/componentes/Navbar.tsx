// Navbar — barra superior fija, minimalista. El logotipo es tipográfico
// (serif) con un filete dorado. El CTA de reservar es el único naranja.

import BotonMagnetico from "../ui/BotonMagnetico";
import "./Navbar.css";

interface Props {
  alReservar: () => void;
}

export default function Navbar({ alReservar }: Props) {
  return (
    <header className="navbar">
      <div className="navbar__inner contenedor">
        <a className="navbar__marca" href="#top">
          <span className="navbar__nombre">The Nail Society</span>
          <span className="navbar__spa">SPA · AGUASCALIENTES</span>
        </a>
        <nav className="navbar__links" aria-label="Secciones">
          <a href="#configurador">Diseña tus uñas</a>
          <a href="#servicios">Servicios</a>
          <a href="#equipo">Equipo</a>
          <a href="#sucursales">Sucursales</a>
        </nav>
        <BotonMagnetico onClick={alReservar} className="navbar__cta">
          Reservar
        </BotonMagnetico>
      </div>
    </header>
  );
}

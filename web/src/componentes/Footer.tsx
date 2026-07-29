// Footer — cierre de marca con las dos sucursales, redes y el WhatsApp del salón.

import "./Footer.css";

export default function Footer() {
  return (
    <footer className="footer seccion-oscura">
      <div className="contenedor footer__inner">
        <div className="footer__marca">
          <span className="footer__nombre">The Nail Society</span>
          <span className="footer__spa">SPA · AGUASCALIENTES</span>
          {/* Acceso al panel del salón. Va discreto y al pie a propósito: es
              para el equipo, no para las clientas, pero tiene que estar a un
              clic desde el teléfono de cualquier empleada. */}
          <a
            className="footer__panel"
            href={`${import.meta.env.VITE_API_URL ?? ""}/panel`}
            target="_blank"
            rel="noopener"
          >
            <span className="footer__panel-icono" aria-hidden="true">
              <svg viewBox="0 0 16 16" width="13" height="13">
                <rect
                  x="3"
                  y="7"
                  width="10"
                  height="7"
                  rx="1.4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.4"
                />
                <path
                  d="M5.6 7V4.9a2.4 2.4 0 0 1 4.8 0V7"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.4"
                />
              </svg>
            </span>
            Panel del equipo
          </a>
        </div>

        <div className="footer__cols">
          <div>
            <h4>Sucursal Norte</h4>
            <p>Blvd. Luis Donaldo Colosio 400</p>
          </div>
          <div>
            <h4>Sucursal Sur</h4>
            <p>Av. Aguascalientes Sur #117, Villa Jardín II</p>
          </div>
          <div>
            <h4>Contacto</h4>
            <p>
              <a href="https://wa.me/524492733769" target="_blank" rel="noopener">
                WhatsApp
              </a>
              <br />
              <a
                href="https://instagram.com/thenailsociety_ags"
                target="_blank"
                rel="noopener"
              >
                @thenailsociety_ags
              </a>
            </p>
          </div>
        </div>
      </div>
      <div className="footer__filete" aria-hidden="true" />
      <p className="footer__nota">
        © {new Date().getFullYear()} The Nail Society Spa · Hecho con cariño en Aguascalientes
      </p>
    </footer>
  );
}

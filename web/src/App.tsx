// App — arma la página pública de The Nail Society Spa.
// Mantiene el estado del "look" (color + acabado) elegido en el configurador y
// lo comparte con la reserva, además de coordinar el scroll entre secciones.

import { useRef, useState } from "react";
import Navbar from "./componentes/Navbar";
import Footer from "./componentes/Footer";
import Hero from "./secciones/Hero";
import Configurador from "./secciones/Configurador";
import Servicios from "./secciones/Servicios";
import Equipo from "./secciones/Equipo";
import Sucursales from "./secciones/Sucursales";
import Reserva from "./secciones/Reserva";
import { CONFIG_INICIAL, type EstadoConfig } from "./escena/materiales";

export default function App() {
  const [config, setConfig] = useState<EstadoConfig>(CONFIG_INICIAL);
  const [lookElegido, setLookElegido] = useState(false);
  const [servicioSugerido, setServicioSugerido] = useState<string | null>(null);

  const reservaRef = useRef<HTMLElement>(null);

  const irA = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  const irAReserva = () => reservaRef.current?.scrollIntoView({ behavior: "smooth" });

  const reservarLook = () => {
    setLookElegido(true);
    irAReserva();
  };

  const reservarServicio = (servicioId: string) => {
    // Se fuerza un cambio de referencia para que Reserva reaccione aunque
    // sea el mismo id que antes.
    setServicioSugerido(null);
    requestAnimationFrame(() => setServicioSugerido(servicioId));
    irAReserva();
  };

  return (
    <>
      <Navbar alReservar={irAReserva} />
      <main>
        <Hero alReservar={irAReserva} alConfigurar={() => irA("configurador")} />
        <Configurador config={config} setConfig={setConfig} alReservar={reservarLook} />
        <Servicios alReservarServicio={reservarServicio} />
        <Equipo />
        <Sucursales alReservar={irAReserva} />
        <Reserva
          ref={reservaRef}
          config={config}
          servicioSugeridoId={servicioSugerido}
          lookElegido={lookElegido}
        />
      </main>
      <Footer />
    </>
  );
}

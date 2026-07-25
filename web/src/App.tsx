// App — arma la página pública de The Nail Society Spa.
// Coordina el scroll entre secciones y la preselección de servicio hacia la
// reserva. (El configurador de color de uñas se retiró; el hero muestra la
// mano 3D en Spline.)

import { useRef, useState } from "react";
import Navbar from "./componentes/Navbar";
import Footer from "./componentes/Footer";
import Hero from "./secciones/Hero";
import Servicios from "./secciones/Servicios";
import Equipo from "./secciones/Equipo";
import Sucursales from "./secciones/Sucursales";
import Reserva from "./secciones/Reserva";

export default function App() {
  const [servicioSugerido, setServicioSugerido] = useState<string | null>(null);

  const reservaRef = useRef<HTMLElement>(null);

  const irA = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  const irAReserva = () => reservaRef.current?.scrollIntoView({ behavior: "smooth" });

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
        <Hero alReservar={irAReserva} alVerServicios={() => irA("servicios")} />
        <Servicios alReservarServicio={reservarServicio} />
        <Equipo />
        <Sucursales alReservar={irAReserva} />
        <Reserva ref={reservaRef} servicioSugeridoId={servicioSugerido} />
      </main>
      <Footer />
    </>
  );
}

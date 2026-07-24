// Sucursales — Norte y Sur. Datos reales del backend cuando existan; si no,
// cae a los datos de referencia del salón. Cada tarjeta con dirección y
// acceso directo a reservar en esa sucursal.

import { useEffect, useState } from "react";
import { obtenerSucursales, type Sucursal } from "../api/reservas";
import TextoRevelado from "../ui/TextoRevelado";
import "./Sucursales.css";

// Respaldo si la API aún no responde (datos de referencia del salón).
const RESPALDO: Sucursal[] = [
  {
    id: "norte",
    nombre: "Norte",
    direccion: "Blvd. Luis Donaldo Colosio 400 · Aguascalientes",
    telefono: null,
  },
  {
    id: "sur",
    nombre: "Sur",
    direccion: "Av. Aguascalientes Sur #117, Villa Jardín II · Aguascalientes",
    telefono: null,
  },
];

interface Props {
  alReservar: () => void;
}

export default function Sucursales({ alReservar }: Props) {
  const [sucursales, setSucursales] = useState<Sucursal[]>(RESPALDO);

  useEffect(() => {
    obtenerSucursales()
      .then((s) => {
        if (s.length) setSucursales(s);
      })
      .catch(() => {
        /* se mantiene el respaldo */
      });
  }, []);

  return (
    <section className="sucursales" id="sucursales">
      <div className="contenedor">
        <div className="sucursales__cabecera">
          <TextoRevelado como="span" className="kicker">
            Dónde encontrarnos
          </TextoRevelado>
          <TextoRevelado como="h2" className="sucursales__titulo" retraso={0.06}>
            Dos sucursales en Aguascalientes
          </TextoRevelado>
        </div>

        <div className="sucursales__grid">
          {sucursales.map((s) => (
            <TextoRevelado key={s.id} className="sucursal">
              <div className="sucursal__marco">
                <span className="sucursal__etiqueta">Sucursal</span>
                <h3 className="sucursal__nombre">{s.nombre}</h3>
                <p className="sucursal__dir">{s.direccion ?? "Aguascalientes"}</p>
                {s.telefono && <p className="sucursal__tel">{s.telefono}</p>}
                <button className="sucursal__cta" onClick={alReservar}>
                  Reservar aquí →
                </button>
              </div>
            </TextoRevelado>
          ))}
        </div>
      </div>
    </section>
  );
}

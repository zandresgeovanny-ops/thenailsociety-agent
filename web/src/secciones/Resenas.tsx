// Reseñas — prueba social. Editorial, en clave "libro de firmas de la Society".
//
// Estructura: columna izquierda fija con el SELLO (medallón dorado que recoge
// el logotipo de la marca) y el desglose por sucursal; columna derecha con las
// citas literales en tipografía itálica serif, como entradas de un libro.
//
// El contenido no vive aquí: viene de ../datos/resenas. Este archivo solo sabe
// pintar. Es la separación que necesita la plantilla para revenderse.

import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import TextoRevelado from "../ui/TextoRevelado";
import BotonMagnetico from "../ui/BotonMagnetico";
import { prefiereMenosMovimiento } from "../lib/preferencias";
import {
  AGREGADOS,
  CALIFICACION_MEDIA,
  RESENAS,
  TEXTOS,
  TOTAL_RESENAS,
} from "../datos/resenas";
import "./Resenas.css";

gsap.registerPlugin(ScrollTrigger, useGSAP);

interface Props {
  alReservar: () => void;
}

/**
 * Fila de cinco estrellas con relleno fraccionario: 4.1 pinta cuatro llenas y
 * un 10% de la quinta. Se resuelve con un degradado que corta exactamente en
 * el porcentaje, no redondeando — la media real no se maquilla.
 */
function Estrellas({ valor, id }: { valor: number; id: string }) {
  const corte = `${(valor / 5) * 100}%`;
  const trazo =
    "M12 2.6l2.72 5.86 6.28.78-4.64 4.4 1.22 6.36L12 16.9l-5.58 3.1 1.22-6.36L3 9.24l6.28-.78L12 2.6z";

  return (
    <svg
      className="resenas__estrellas"
      viewBox="0 0 124 24"
      role="img"
      aria-label={`${valor} de 5 estrellas`}
    >
      <defs>
        <linearGradient id={`relleno-${id}`} x1="0" x2="1" y1="0" y2="0">
          <stop offset={corte} stopColor="var(--acento)" />
          <stop offset={corte} stopColor="transparent" />
        </linearGradient>
      </defs>
      {[0, 1, 2, 3, 4].map((i) => (
        <g key={i} transform={`translate(${i * 25} 0)`}>
          {/* Contorno siempre visible: da la referencia de "sobre cinco". */}
          <path d={trazo} fill="none" stroke="var(--acento)" strokeWidth="1" opacity="0.42" />
          <path d={trazo} fill={`url(#relleno-${id})`} />
        </g>
      ))}
    </svg>
  );
}

export default function Resenas({ alReservar }: Props) {
  const seccion = useRef<HTMLElement>(null);
  const cifra = useRef<HTMLSpanElement>(null);
  const aro = useRef<SVGCircleElement>(null);

  useGSAP(
    () => {
      if (prefiereMenosMovimiento()) return;

      // La cifra sube hasta la media real al entrar la sección. Es el dato que
      // más pesa de toda la página: merece que el ojo lo vea "llegar".
      const contador = { n: 0 };
      gsap.to(contador, {
        n: CALIFICACION_MEDIA,
        duration: 1.5,
        ease: "power2.out",
        scrollTrigger: { trigger: seccion.current, start: "top 68%", once: true },
        onUpdate: () => {
          if (cifra.current) cifra.current.textContent = contador.n.toFixed(1);
        },
      });

      // El aro del sello se traza como si alguien lo estuviera grabando.
      if (aro.current) {
        const largo = aro.current.getTotalLength();
        gsap.fromTo(
          aro.current,
          { strokeDasharray: largo, strokeDashoffset: largo },
          {
            strokeDashoffset: 0,
            duration: 1.8,
            ease: "power2.inOut",
            scrollTrigger: { trigger: seccion.current, start: "top 68%", once: true },
          },
        );
      }
    },
    { scope: seccion },
  );

  const [titulo1, titulo2] = TEXTOS.titulo.split("\n");

  return (
    <section className="resenas" id="resenas" ref={seccion}>
      <span className="resenas__indice" aria-hidden="true">
        04
      </span>

      <div className="contenedor resenas__grid">
        {/* ── Columna fija: el sello y el desglose por sucursal ── */}
        <aside className="resenas__sello-col">
          <div className="resenas__sello">
            <svg className="resenas__medalla" viewBox="0 0 220 220" aria-hidden="true">
              <defs>
                <path
                  id="orbita"
                  d="M110,110 m-84,0 a84,84 0 1,1 168,0 a84,84 0 1,1 -168,0"
                />
              </defs>

              {/* Doble filete: el marco de sello que describe la guía de marca */}
              <circle cx="110" cy="110" r="96" className="resenas__aro-fino" />
              <circle ref={aro} cx="110" cy="110" r="88" className="resenas__aro" />

              <text className="resenas__orbita">
                <textPath href="#orbita" startOffset="0%">
                  THE NAIL SOCIETY · AGUASCALIENTES · NORTE &amp; SUR ·
                </textPath>
              </text>
            </svg>

            <div className="resenas__nucleo">
              <span className="resenas__cifra" ref={cifra}>
                {CALIFICACION_MEDIA.toFixed(1)}
              </span>
              <Estrellas valor={CALIFICACION_MEDIA} id="media" />
              <span className="resenas__total">{TOTAL_RESENAS} reseñas en Google</span>
            </div>
          </div>

          <ul className="resenas__sucursales">
            {AGREGADOS.map((a) => (
              <li key={a.sucursal} className="resenas__suc">
                <span className="resenas__suc-nombre">Sucursal {a.sucursal}</span>
                <span className="resenas__suc-dato">
                  <b>{a.calificacion.toFixed(1)}</b>
                  <i>/ {a.total} reseñas</i>
                </span>
                {/* Barra proporcional sobre 5: comparación honesta entre sucursales */}
                <span
                  className="resenas__suc-barra"
                  style={{ ["--llena" as string]: `${(a.calificacion / 5) * 100}%` }}
                  aria-hidden="true"
                />
              </li>
            ))}
          </ul>

          <p className="resenas__pie">{TEXTOS.pie}</p>
        </aside>

        {/* ── Columna de citas: el libro propiamente dicho ── */}
        <div className="resenas__libro">
          <header className="resenas__cabecera">
            <TextoRevelado como="span" className="kicker">
              {TEXTOS.kicker}
            </TextoRevelado>
            <TextoRevelado como="h2" className="resenas__titulo" retraso={0.06}>
              {titulo1}
              <br />
              <em>{titulo2}</em>
            </TextoRevelado>
            <TextoRevelado como="p" className="resenas__entrada" retraso={0.12}>
              {TEXTOS.entrada}
            </TextoRevelado>
          </header>

          <div className="resenas__lista">
            {RESENAS.map((r, i) => (
              <TextoRevelado
                key={`${r.autor}-${i}`}
                como="figure"
                className="resena"
                retraso={0.06 * (i % 2)}
              >
                <span className="resena__comilla" aria-hidden="true">
                  &ldquo;
                </span>
                <blockquote className="resena__texto">{r.texto}</blockquote>
                <span className="resena__filete" aria-hidden="true" />
                <figcaption className="resena__firma">
                  <span className="resena__autor">{r.autor}</span>
                  <span className="resena__meta">
                    {r.sucursal} · {r.fecha}
                  </span>
                </figcaption>
              </TextoRevelado>
            ))}
          </div>

          <TextoRevelado className="resenas__cierre" retraso={0.1}>
            <p className="resenas__invitacion">{TEXTOS.invitacion}</p>
            <BotonMagnetico onClick={alReservar}>Apartar mi lugar</BotonMagnetico>
          </TextoRevelado>
        </div>
      </div>
    </section>
  );
}

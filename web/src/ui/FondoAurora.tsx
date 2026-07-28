// FondoAurora — auroras suaves de luz dorada y champán que respiran detrás del
// contenido. Puramente decorativo (aria-hidden). Se congela con movimiento reducido.

import "./FondoAurora.css";

export default function FondoAurora({ variante = "claro" }: { variante?: "claro" | "oscuro" }) {
  return (
    <div className={`aurora aurora--${variante}`} aria-hidden="true">
      <span className="aurora__mancha a" />
      <span className="aurora__mancha b" />
      <span className="aurora__mancha c" />
    </div>
  );
}

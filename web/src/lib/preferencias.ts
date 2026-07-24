// Hooks de preferencias del dispositivo: movimiento reducido y gama baja.
// Se usan para degradar con elegancia el configurador 3D en equipos modestos
// o cuando la persona pidió menos animación en su sistema.

import { useEffect, useState } from "react";

/** True si el sistema pide movimiento reducido (accesibilidad). */
export function usaMovimientoReducido(): boolean {
  const [reducido, setReducido] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const actualizar = () => setReducido(mq.matches);
    actualizar();
    mq.addEventListener("change", actualizar);
    return () => mq.removeEventListener("change", actualizar);
  }, []);

  return reducido;
}

/**
 * Heurística de gama baja: pocos núcleos lógicos o poca RAM.
 * En estos equipos evitamos montar el Canvas 3D y mostramos una versión ligera.
 */
export function esEquipoGamaBaja(): boolean {
  if (typeof navigator === "undefined") return false;
  const nucleos = navigator.hardwareConcurrency ?? 8;
  // deviceMemory no está en todos los navegadores; cuando falta, no penalizamos.
  const memoria = (navigator as Navigator & { deviceMemory?: number }).deviceMemory ?? 8;
  return nucleos <= 4 || memoria <= 4;
}

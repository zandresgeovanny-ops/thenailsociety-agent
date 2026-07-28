// Prueba social de The Nail Society Spa.
//
// FUENTE ÚNICA: knowledge/thenailsociety_resenas_google.csv (Google Maps).
// Nada de esto se inventa ni se reescribe. Si un dato no está en el CSV, no
// aparece aquí.
//
// ── Dos decisiones que hay que conocer antes de tocar este archivo ──────
//
// 1. Las citas van LITERALES, con la ortografía original ("esta Hermoso",
//    "super cutes"). Es lo que da veracidad: una reseña pulida se lee como
//    copy y deja de convencer. Solo se reparó el mojibake del CSV
//    ("Dise�os" → "Diseños"), que es corrupción de codificación, no ortografía.
//
// 2. NO se publica la calificación individual de cada reseña. En el CSV las
//    estrellas no concuerdan con el texto — hay reseñas de 1★ que dicen
//    "Excelente Servicio" y de 2★ que dicen "super cutes y bonitos". El
//    scrape quedó mal. Publicar esas estrellas sería mostrar un dato falso,
//    así que se muestran solo los AGREGADOS por sucursal, que sí son fiables.
//    Si algún día se reescrapea con estrellas correctas, se añade el campo y
//    la tarjeta las pinta.

/** Agregado real de una sucursal en Google Maps. */
export interface AgregadoSucursal {
  sucursal: string;
  calificacion: number;
  total: number;
}

/** Reseña individual, tal cual aparece publicada. */
export interface Resena {
  autor: string;
  sucursal: string;
  /** Antigüedad tal como la reporta Google ("Hace 3 meses"). */
  fecha: string;
  /** Texto literal. No editar. */
  texto: string;
}

export const AGREGADOS: AgregadoSucursal[] = [
  { sucursal: "Norte", calificacion: 4.2, total: 80 },
  { sucursal: "Sur", calificacion: 3.9, total: 70 },
];

export const RESENAS: Resena[] = [
  {
    autor: "Florencia Ortega",
    sucursal: "Sur",
    fecha: "Hace 3 años",
    texto:
      "Me encanta! Variedad de colores en gelish y la atención es excelente y siempre te ofrecen bebida durante tu estancia.",
  },
  {
    autor: "Nancy Gomez",
    sucursal: "Norte",
    fecha: "Hace 2 meses",
    texto: "Siempre me agrada su servicio y comodidad. Lo recomiendo ampliamente.",
  },
  {
    autor: "Ana Karen",
    sucursal: "Sur",
    fecha: "Hace un año",
    texto: "Mi manicura y mi gelish esta Hermoso gracias a ellas",
  },
  {
    autor: "TRAVEL PASSPORT",
    sucursal: "Norte",
    fecha: "3 semanas atrás",
    texto: "Excelente Servicio, muy buenas manicuristas!!",
  },
  {
    autor: "Anahi Ramirez",
    sucursal: "Sur",
    fecha: "Hace 4 meses",
    texto: "Diseños super cutes y bonitos fueron muy rapidas en su trabajo",
  },
  {
    autor: "rafael garcia",
    sucursal: "Norte",
    fecha: "Hace un año",
    texto: "Ambiente agradable con las manicuristas",
  },
];

/** Suma de reseñas de todas las sucursales. */
export const TOTAL_RESENAS = AGREGADOS.reduce((n, a) => n + a.total, 0);

/**
 * Calificación media ponderada por número de reseñas — no el promedio simple
 * de los promedios, que sobrerrepresentaría a la sucursal más pequeña.
 */
export const CALIFICACION_MEDIA =
  Math.round(
    (AGREGADOS.reduce((n, a) => n + a.calificacion * a.total, 0) / TOTAL_RESENAS) * 10,
  ) / 10;

/** Copy de la sección. Vive aquí para que la plantilla lo cambie sin tocar el JSX. */
export const TEXTOS = {
  kicker: "El libro de la Society",
  titulo: "Lo que dicen quienes\nya se sentaron aquí",
  entrada:
    "Cada reseña llega de Google, sin retocar. Así se escriben cuando una sale del salón.",
  pie: "Reseñas públicas de Google Maps, transcritas tal cual.",
  invitacion: "¿Te reservamos un lugar?",
} as const;

// Materiales del configurador de uñas.
// Cada "acabado" ajusta las propiedades de un MeshPhysicalMaterial para imitar
// el look real del esmalte: gel brillante, mate, metálico o glitter.

export type ClaveAcabado = "gel" | "mate" | "metalico" | "glitter";

export interface Acabado {
  clave: ClaveAcabado;
  nombre: string;
  // Props que se derraman sobre <meshPhysicalMaterial>
  props: {
    roughness: number;
    metalness: number;
    clearcoat: number;
    clearcoatRoughness: number;
    sheen?: number;
    sheenRoughness?: number;
    iridescence?: number;
    iridescenceIOR?: number;
  };
}

export const ACABADOS: Acabado[] = [
  {
    clave: "gel",
    nombre: "Gel",
    // Esmalte gel: capa transparente muy pulida sobre color saturado.
    props: { roughness: 0.12, metalness: 0.0, clearcoat: 1, clearcoatRoughness: 0.04 },
  },
  {
    clave: "mate",
    nombre: "Mate",
    // Acabado mate: sin brillo especular, tacto aterciopelado.
    props: {
      roughness: 0.85,
      metalness: 0.0,
      clearcoat: 0.15,
      clearcoatRoughness: 0.6,
      sheen: 0.4,
      sheenRoughness: 0.8,
    },
  },
  {
    clave: "metalico",
    nombre: "Metálico",
    // Cromado suave: reflejo metálico con laca encima.
    props: { roughness: 0.22, metalness: 0.9, clearcoat: 1, clearcoatRoughness: 0.1 },
  },
  {
    clave: "glitter",
    nombre: "Glitter",
    // Destellos: iridiscencia + brillo alto para el efecto escarcha.
    props: {
      roughness: 0.28,
      metalness: 0.55,
      clearcoat: 1,
      clearcoatRoughness: 0.15,
      iridescence: 0.8,
      iridescenceIOR: 1.6,
    },
  },
];

// Paleta de colores de esmalte que combina con la marca (nudes, rojos, joya,
// más el naranja de acento y tonos oscuros). El valor es el color base del material.
export interface ColorEsmalte {
  nombre: string;
  hex: string;
}

export const COLORES: ColorEsmalte[] = [
  { nombre: "Nude rosado", hex: "#e8c4b8" },
  { nombre: "Beige seda", hex: "#dcc7a8" },
  { nombre: "Rosa palo", hex: "#d98c9c" },
  { nombre: "Rojo carmín", hex: "#a01f2e" },
  { nombre: "Vino", hex: "#5c1f2e" },
  { nombre: "Naranja spa", hex: "#e8782c" },
  { nombre: "Coral", hex: "#e26d5c" },
  { nombre: "Oro champaña", hex: "#c9a24d" },
  { nombre: "Verde jade", hex: "#2f6b5e" },
  { nombre: "Azul noche", hex: "#26324a" },
  { nombre: "Lila", hex: "#8a6fa8" },
  { nombre: "Negro ónix", hex: "#161616" },
];

// Estado del configurador que comparten la escena 3D y el panel de reserva.
export interface EstadoConfig {
  color: ColorEsmalte;
  acabado: Acabado;
}

export const CONFIG_INICIAL: EstadoConfig = {
  color: COLORES[0],
  acabado: ACABADOS[0],
};

// Mano.tsx — la mano del configurador.
//
// Estrategia: intenta cargar un modelo real /modelos/mano.glb. Mientras ese
// archivo no exista (o falle), cae a una mano PROCEDURAL para no bloquear el
// desarrollo. En cuanto dejes el .glb en web/public/modelos/, cambia
// HAY_MODELO a true (o define VITE_MODELO_MANO) y el loader lo usará; las uñas
// se pintan igual con el material configurable.

import { useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import type { EstadoConfig } from "./materiales";

// Ponlo en true cuando exista web/public/modelos/mano.glb
const HAY_MODELO = import.meta.env.VITE_MODELO_MANO === "1";
const RUTA_MODELO = "/modelos/mano.glb";

interface PropsMano {
  config: EstadoConfig;
}

// ─────────────────────────────────────────────────────────────
// Material configurable de las uñas (color + acabado en vivo)
// ─────────────────────────────────────────────────────────────
function MaterialUna({ config }: PropsMano) {
  return (
    <meshPhysicalMaterial
      color={config.color.hex}
      {...config.acabado.props}
      envMapIntensity={1.1}
    />
  );
}

// Una uña: elipsoide achatado y curvado, ligeramente elevado sobre la yema.
function Una({
  config,
  posicion,
  escala = 1,
  rotacion = [0, 0, 0],
}: PropsMano & {
  posicion: [number, number, number];
  escala?: number;
  rotacion?: [number, number, number];
}) {
  return (
    <mesh
      position={posicion}
      rotation={rotacion}
      scale={[0.17 * escala, 0.24 * escala, 0.09 * escala]}
      castShadow
    >
      <sphereGeometry args={[1, 32, 24]} />
      <MaterialUna config={config} />
    </mesh>
  );
}

// Configuración de los 4 dedos (meñique → índice); el medio es el más largo.
const DEDOS: { x: number; base: number; largo: number; r: number; inclina: number }[] = [
  { x: -0.66, base: 0.62, largo: 0.95, r: 0.145, inclina: -0.14 },
  { x: -0.24, base: 0.74, largo: 1.28, r: 0.155, inclina: -0.05 },
  { x: 0.2, base: 0.78, largo: 1.4, r: 0.16, inclina: 0.04 },
  { x: 0.6, base: 0.68, largo: 1.16, r: 0.15, inclina: 0.13 },
];

function Dedo({
  config,
  x,
  base,
  largo,
  r,
  inclina,
}: PropsMano & { x: number; base: number; largo: number; r: number; inclina: number }) {
  const centroY = base + largo / 2;
  const puntaY = base + largo;
  return (
    <group rotation={[0, 0, inclina]}>
      {/* falange */}
      <mesh position={[x, centroY, 0]} castShadow>
        <capsuleGeometry args={[r, largo, 8, 16]} />
        <meshStandardMaterial color="#e7c3ad" roughness={0.68} metalness={0} />
      </mesh>
      {/* uña en la yema, empujada al frente (+Z) y mirando hacia arriba */}
      <Una
        config={config}
        posicion={[x, puntaY - 0.02, r * 0.72]}
        escala={r / 0.16}
        rotacion={[-0.5, 0, 0]}
      />
    </group>
  );
}

// ─────────────────────────────────────────────────────────────
// Mano procedural completa
// ─────────────────────────────────────────────────────────────
function ManoProcedural({ config }: PropsMano) {
  const materialPiel = useMemo(
    () => new THREE.MeshStandardMaterial({ color: "#e7c3ad", roughness: 0.7, metalness: 0 }),
    [],
  );

  return (
    <group position={[0, -0.6, 0]}>
      {/* palma */}
      <mesh position={[0, 0.1, 0]} scale={[1, 1, 0.55]} castShadow receiveShadow>
        <boxGeometry args={[1.55, 1.5, 1]} />
        <primitive object={materialPiel} attach="material" />
      </mesh>
      {/* redondeo de nudillos */}
      <mesh position={[0, 0.78, 0]} scale={[1, 0.5, 0.55]}>
        <sphereGeometry args={[0.8, 24, 16]} />
        <primitive object={materialPiel} attach="material" />
      </mesh>
      {/* base de la muñeca */}
      <mesh position={[0, -0.85, 0]} scale={[0.85, 0.7, 0.5]}>
        <sphereGeometry args={[0.8, 24, 16]} />
        <primitive object={materialPiel} attach="material" />
      </mesh>

      {/* dedos */}
      {DEDOS.map((d, i) => (
        <Dedo key={i} config={config} {...d} />
      ))}

      {/* pulgar (dedo lateral inclinado) con su uña */}
      <group position={[-0.78, -0.15, 0.1]} rotation={[0, 0, 1.05]}>
        <mesh position={[0, 0.42, 0]} castShadow>
          <capsuleGeometry args={[0.16, 0.72, 8, 16]} />
          <primitive object={materialPiel} attach="material" />
        </mesh>
        <Una config={config} posicion={[0, 0.82, 0.12]} escala={1} rotacion={[-0.5, 0, -0.2]} />
      </group>
    </group>
  );
}

// ─────────────────────────────────────────────────────────────
// Mano desde modelo GLB (se activa cuando exista el archivo)
// ─────────────────────────────────────────────────────────────
function ManoModelo({ config }: PropsMano) {
  const { scene } = useGLTF(RUTA_MODELO);
  const clon = useMemo(() => scene.clone(true), [scene]);

  // Pinta con el material configurable las mallas cuyo nombre contenga "una"/"nail".
  useMemo(() => {
    clon.traverse((obj) => {
      if (obj instanceof THREE.Mesh && /u[nñ]a|nail/i.test(obj.name)) {
        obj.material = new THREE.MeshPhysicalMaterial({
          color: new THREE.Color(config.color.hex),
          ...config.acabado.props,
          envMapIntensity: 1.1,
        });
      }
    });
  }, [clon, config]);

  return <primitive object={clon} />;
}

export default function Mano({ config }: PropsMano) {
  return HAY_MODELO ? <ManoModelo config={config} /> : <ManoProcedural config={config} />;
}

// Precarga sólo si el modelo está declarado, para no provocar 404 en desarrollo.
if (HAY_MODELO) {
  useGLTF.preload(RUTA_MODELO);
}

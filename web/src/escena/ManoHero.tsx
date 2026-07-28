// ManoHero — la mano 3D del hero, renderizada con React Three Fiber.
// Carga el modelo glTF real (knowledge/female_hand → public/modelos) y le
// superpone 5 "uñas de gel" con un material propio: así podemos darles un
// color vibrante ALEATORIO en cada carga sin teñir la piel (el modelo trae
// piel y uñas horneadas en un solo material).
//
// El acercamiento/intercambio al hacer scroll NO vive aquí: lo maneja Hero.tsx
// a nivel del DOM (mueve los bloques). Aquí solo hay una flotación sutil.

import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { useGLTF, Environment, Center } from "@react-three/drei";
import * as THREE from "three";
import { prefiereMenosMovimiento } from "../lib/preferencias";

const RUTA_MODELO = "/modelos/female_hand/scene.gltf";

// Paleta de esmaltes: los acabados que el salón muestra en su feed.
// La guía de marca los llama "quiet luxury" y prohíbe expresamente los tonos
// saturados o infantiles, así que aquí no entra ningún neón.
// nude rosado · beige · champán · blanco lechoso · gelish translúcido
const PALETA = ["#D8A98F", "#E3CDB6", "#DFC49A", "#F2ECE4", "#E8CFC6"];

// Posición / rotación / escala de cada uña de gel, en coordenadas locales del
// grupo de la mano. Se afinan contra el modelo real. (x: ancho, y: alto,
// z: largo del dedo — las yemas están hacia z alto).
type Una = { pos: [number, number, number]; rot: [number, number, number]; scale: number };
const UNAS: Una[] = [
  { pos: [-3.4, 0.9, 21.8], rot: [0.5, 0, 0.1], scale: 1.15 },  // meñique
  { pos: [-1.3, 1.4, 24.0], rot: [0.5, 0, 0.05], scale: 1.35 }, // anular
  { pos: [0.9, 1.6, 24.6], rot: [0.5, 0, 0], scale: 1.4 },      // medio
  { pos: [3.0, 1.4, 23.4], rot: [0.5, 0, -0.05], scale: 1.3 },  // índice
  { pos: [5.6, 0.2, 17.0], rot: [0.4, 0.2, -0.5], scale: 1.25 }, // pulgar
];

const reduce = prefiereMenosMovimiento();

// Una uña de gel: media cápsula aplanada con material físico (acabado esmalte).
function UnaGel({ una, color }: { una: Una; color: string }) {
  return (
    <mesh position={una.pos} rotation={una.rot} scale={[una.scale, una.scale * 0.55, una.scale * 1.5]}>
      {/* esfera aplanada = uña bombeada */}
      <sphereGeometry args={[0.9, 24, 16]} />
      <meshPhysicalMaterial
        color={color}
        roughness={0.12}
        metalness={0}
        clearcoat={1}
        clearcoatRoughness={0.05}
        reflectivity={0.6}
        sheen={0.4}
      />
    </mesh>
  );
}

function Mano({ color }: { color: string }) {
  const { scene } = useGLTF(RUTA_MODELO);
  // Clonamos para no mutar la caché de useGLTF entre montajes.
  const modelo = useMemo(() => scene.clone(true), [scene]);
  return (
    <group>
      <primitive object={modelo} />
      {UNAS.map((una, i) => (
        <UnaGel key={i} una={una} color={color} />
      ))}
    </group>
  );
}

// Grupo que flota suavemente y encuadra la mano.
function Escena({ color }: { color: string }) {
  const grupo = useRef<THREE.Group>(null);
  useFrame((state) => {
    if (reduce || !grupo.current) return;
    const t = state.clock.elapsedTime;
    grupo.current.rotation.y = Math.sin(t * 0.3) * 0.12;
    grupo.current.position.y = Math.sin(t * 0.6) * 0.15;
  });
  return (
    <group ref={grupo}>
      {/* Center normaliza el pivote del modelo (que viene desplazado en z). */}
      <Center>
        <group scale={0.12} rotation={[0, -0.4, 0]}>
          <Mano color={color} />
        </group>
      </Center>
    </group>
  );
}

export default function ManoHero() {
  // Color aleatorio fijado UNA vez por montaje de la página.
  const color = useMemo(() => PALETA[Math.floor(Math.random() * PALETA.length)], []);

  return (
    <div className="mano-hero">
      <Canvas
        className="mano-hero__canvas"
        dpr={[1, 2]}
        camera={{ position: [0, 0.2, 5.2], fov: 40 }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[3, 4, 5]} intensity={1.1} />
        <directionalLight position={[-4, 2, -2]} intensity={0.4} color="#c9a24d" />
        <Suspense fallback={null}>
          <Escena color={color} />
          <Environment preset="studio" />
        </Suspense>
      </Canvas>
    </div>
  );
}

useGLTF.preload(RUTA_MODELO);

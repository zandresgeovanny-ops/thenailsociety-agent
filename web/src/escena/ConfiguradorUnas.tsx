// ConfiguradorUnas.tsx — el Canvas 3D del configurador.
//
// Muestra la mano con las uñas pintadas según el estado {color, acabado}.
// Iluminación de estudio hecha con Lightformers (sin descargar HDRIs externos,
// para que funcione offline y sin depender de CDNs).
//
// Accesibilidad y rendimiento:
//  - En equipos de gama baja NO se monta el Canvas: se muestra una vista ligera.
//  - Con prefers-reduced-motion se congela el giro automático.

import { Suspense, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Lightformer, OrbitControls, ContactShadows } from "@react-three/drei";
import type { Group } from "three";
import Mano from "./Mano";
import type { EstadoConfig } from "./materiales";
import { usaMovimientoReducido, esEquipoGamaBaja } from "../lib/preferencias";

interface Props {
  config: EstadoConfig;
}

// Giro suave e idle de la mano.
function ManoAnimada({ config, quieto }: Props & { quieto: boolean }) {
  const ref = useRef<Group>(null);
  useFrame((estado) => {
    if (!ref.current || quieto) return;
    const t = estado.clock.getElapsedTime();
    ref.current.rotation.y = Math.sin(t * 0.35) * 0.5;
    ref.current.position.y = Math.sin(t * 0.8) * 0.04;
  });
  return (
    <group ref={ref}>
      <Mano config={config} />
    </group>
  );
}

// Vista ligera sin WebGL: un disco con el color y acabado elegidos.
function VistaLigera({ config }: Props) {
  const brillo =
    config.acabado.clave === "mate"
      ? "none"
      : "radial-gradient(circle at 32% 28%, rgba(255,255,255,.7), transparent 42%)";
  return (
    <div
      role="img"
      aria-label={`Muestra de esmalte ${config.color.nombre}, acabado ${config.acabado.nombre}`}
      style={{
        display: "grid",
        placeItems: "center",
        width: "100%",
        height: "100%",
        minHeight: 340,
      }}
    >
      <div
        style={{
          width: "min(62%, 240px)",
          aspectRatio: "1",
          borderRadius: "50%",
          background: config.color.hex,
          boxShadow: "0 24px 60px rgba(0,0,0,.28), inset 0 2px 10px rgba(255,255,255,.25)",
          position: "relative",
          border: "2px solid var(--oro)",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            background: brillo,
          }}
        />
      </div>
    </div>
  );
}

export default function ConfiguradorUnas({ config }: Props) {
  const reducido = usaMovimientoReducido();
  const gamaBaja = esEquipoGamaBaja();

  if (gamaBaja) return <VistaLigera config={config} />;

  return (
    <Canvas
      shadows
      dpr={[1, 2]}
      camera={{ position: [0, 0.2, 4.4], fov: 38 }}
      gl={{ antialias: true, alpha: true }}
      style={{ width: "100%", height: "100%", minHeight: 340 }}
    >
      <ambientLight intensity={0.35} />
      <spotLight
        position={[3, 5, 4]}
        angle={0.5}
        penumbra={0.8}
        intensity={2.4}
        castShadow
        shadow-mapSize={[1024, 1024]}
      />
      <directionalLight position={[-4, 2, -2]} intensity={0.6} color="#e8cf8f" />

      <Suspense fallback={null}>
        <ManoAnimada config={config} quieto={reducido} />

        {/* Estudio de reflejos para la laca (clearcoat) */}
        <Environment resolution={256}>
          <Lightformer intensity={2.4} position={[0, 3, 2]} scale={[6, 3, 1]} color="#ffffff" />
          <Lightformer intensity={1.2} position={[-3, 1, 2]} scale={[3, 3, 1]} color="#f4efe6" />
          <Lightformer intensity={1.6} position={[3, -1, 2]} scale={[3, 3, 1]} color="#e8cf8f" />
          <Lightformer
            intensity={0.8}
            position={[0, -3, -2]}
            scale={[6, 3, 1]}
            color="#c9a24d"
          />
        </Environment>

        <ContactShadows
          position={[0, -2.1, 0]}
          opacity={0.5}
          scale={8}
          blur={2.6}
          far={4}
          color="#3a2a10"
        />
      </Suspense>

      <OrbitControls
        enablePan={false}
        enableZoom={false}
        minPolarAngle={Math.PI / 3}
        maxPolarAngle={Math.PI / 1.8}
        rotateSpeed={0.6}
      />
    </Canvas>
  );
}

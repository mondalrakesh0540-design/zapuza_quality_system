'use client';

import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { Hotspot } from '@/types/vehicle';
import { Html } from '@react-three/drei';

interface ProceduralCarProps {
  color: string;
  wireframe: boolean;
  modelType?: 'hypercar' | 'suv' | 'sports-coupe' | 'luxury-sedan' | 'ev-crossover';
  hotspots?: Hotspot[];
  showHotspots: boolean;
  selectedHotspot: Hotspot | null;
  onSelectHotspot: (hotspot: Hotspot) => void;
  autoRotate: boolean;
}

export function ProceduralCar({
  color,
  wireframe,
  modelType = 'sports-coupe',
  hotspots = [],
  showHotspots = true,
  selectedHotspot,
  onSelectHotspot,
  autoRotate,
}: ProceduralCarProps) {
  const groupRef = useRef<THREE.Group>(null);
  const wheelsRef = useRef<THREE.Group[]>([]);

  // Slow turntable rotation when autoRotate is enabled
  useFrame((_, delta) => {
    if (autoRotate && groupRef.current) {
      groupRef.current.rotation.y += delta * 0.25;
    }
  });

  // Calculate body proportions based on vehicle type
  const isSUV = modelType === 'suv' || modelType === 'ev-crossover';
  const isHypercar = modelType === 'hypercar';
  
  const bodyHeight = isSUV ? 0.9 : isHypercar ? 0.45 : 0.6;
  const bodyY = isSUV ? 0.75 : isHypercar ? 0.45 : 0.55;
  const cabinY = isSUV ? 1.4 : isHypercar ? 0.78 : 0.95;
  const cabinHeight = isSUV ? 0.65 : isHypercar ? 0.35 : 0.45;
  const wheelRadius = isSUV ? 0.42 : isHypercar ? 0.35 : 0.38;
  const wheelWidth = isHypercar ? 0.32 : 0.26;
  const rideHeight = isSUV ? 0.42 : isHypercar ? 0.26 : 0.32;

  return (
    <group ref={groupRef} position={[0, rideHeight, 0]}>
      {/* --- MAIN CHASSIS BODY --- */}
      <mesh position={[0, bodyY, 0]} castShadow receiveShadow>
        <boxGeometry args={[1.9, bodyHeight, 4.4]} />
        <meshPhysicalMaterial
          color={color}
          roughness={0.15}
          metalness={0.85}
          clearcoat={1.0}
          clearcoatRoughness={0.1}
          reflectivity={0.9}
          wireframe={wireframe}
        />
      </mesh>

      {/* --- NOSE HOOD SLOPE --- */}
      <mesh position={[0, bodyY - 0.05, 1.8]} rotation={[-0.15, 0, 0]} castShadow receiveShadow>
        <boxGeometry args={[1.86, bodyHeight * 0.7, 1.0]} />
        <meshPhysicalMaterial
          color={color}
          roughness={0.15}
          metalness={0.85}
          clearcoat={1.0}
          clearcoatRoughness={0.1}
          wireframe={wireframe}
        />
      </mesh>

      {/* --- FRONT BUMPER / CARBON SPLITTER --- */}
      <mesh position={[0, bodyY - bodyHeight * 0.35, 2.25]} castShadow>
        <boxGeometry args={[1.92, 0.12, 0.4]} />
        <meshStandardMaterial color="#111317" roughness={0.3} metalness={0.7} />
      </mesh>

      {/* --- FRONT GRILLE / INTAKES --- */}
      <mesh position={[0, bodyY - 0.1, 2.22]}>
        <boxGeometry args={[1.4, 0.28, 0.05]} />
        <meshStandardMaterial color="#05070a" roughness={0.8} />
      </mesh>

      {/* --- REAR DIFFUSER --- */}
      <mesh position={[0, bodyY - bodyHeight * 0.35, -2.25]} castShadow>
        <boxGeometry args={[1.9, 0.15, 0.4]} />
        <meshStandardMaterial color="#111317" roughness={0.3} metalness={0.8} />
      </mesh>

      {/* --- CABIN / ROOF GREENHOUSE --- */}
      <mesh position={[0, cabinY, -0.2]} castShadow receiveShadow>
        <boxGeometry args={[1.5, cabinHeight, isSUV ? 2.4 : 2.0]} />
        <meshPhysicalMaterial
          color={color}
          roughness={0.15}
          metalness={0.85}
          clearcoat={1.0}
          clearcoatRoughness={0.1}
          wireframe={wireframe}
        />
      </mesh>

      {/* --- WINDSHIELD & WINDOWS (DARK TINTED GLASS) --- */}
      {/* Front Windshield */}
      <mesh position={[0, cabinY, isSUV ? 0.95 : 0.8]} rotation={[-0.6, 0, 0]} castShadow>
        <boxGeometry args={[1.44, 0.05, 0.85]} />
        <meshPhysicalMaterial
          color="#0f1923"
          roughness={0.05}
          transmission={0.85}
          thickness={0.5}
          transparent
          opacity={0.88}
        />
      </mesh>

      {/* Rear Windshield */}
      <mesh position={[0, cabinY, isSUV ? -1.35 : -1.15]} rotation={[0.55, 0, 0]} castShadow>
        <boxGeometry args={[1.44, 0.05, 0.8]} />
        <meshPhysicalMaterial
          color="#0f1923"
          roughness={0.05}
          transmission={0.85}
          thickness={0.5}
          transparent
          opacity={0.88}
        />
      </mesh>

      {/* Side Windows Left & Right */}
      <mesh position={[0.76, cabinY - 0.02, -0.2]}>
        <boxGeometry args={[0.04, cabinHeight * 0.8, isSUV ? 2.1 : 1.7]} />
        <meshPhysicalMaterial color="#0b1117" roughness={0.1} transmission={0.7} transparent opacity={0.9} />
      </mesh>
      <mesh position={[-0.76, cabinY - 0.02, -0.2]}>
        <boxGeometry args={[0.04, cabinHeight * 0.8, isSUV ? 2.1 : 1.7]} />
        <meshPhysicalMaterial color="#0b1117" roughness={0.1} transmission={0.7} transparent opacity={0.9} />
      </mesh>

      {/* --- HEADLIGHTS (CYAN/WHITE LED GLOW) --- */}
      <mesh position={[0.7, bodyY + 0.08, 2.18]}>
        <boxGeometry args={[0.38, 0.1, 0.12]} />
        <meshStandardMaterial
          color="#e0f7ff"
          emissive="#00f0ff"
          emissiveIntensity={3.0}
          toneMapped={false}
        />
      </mesh>
      <mesh position={[-0.7, bodyY + 0.08, 2.18]}>
        <boxGeometry args={[0.38, 0.1, 0.12]} />
        <meshStandardMaterial
          color="#e0f7ff"
          emissive="#00f0ff"
          emissiveIntensity={3.0}
          toneMapped={false}
        />
      </mesh>

      {/* --- TAILLIGHTS (EMISSIVE RED LIGHTBAR) --- */}
      <mesh position={[0, bodyY + 0.08, -2.22]}>
        <boxGeometry args={[1.7, 0.08, 0.08]} />
        <meshStandardMaterial
          color="#ff1a1a"
          emissive="#ff1a1a"
          emissiveIntensity={3.5}
          toneMapped={false}
        />
      </mesh>

      {/* --- SIDE MIRRORS --- */}
      <mesh position={[0.92, cabinY - 0.15, 0.65]} castShadow>
        <boxGeometry args={[0.22, 0.1, 0.14]} />
        <meshStandardMaterial color="#111317" roughness={0.3} metalness={0.7} />
      </mesh>
      <mesh position={[-0.92, cabinY - 0.15, 0.65]} castShadow>
        <boxGeometry args={[0.22, 0.1, 0.14]} />
        <meshStandardMaterial color="#111317" roughness={0.3} metalness={0.7} />
      </mesh>

      {/* --- HYPERCAR REAR WING (IF HYPERCAR OR GT3) --- */}
      {isHypercar && (
        <group position={[0, bodyY + 0.45, -2.0]}>
          <mesh castShadow>
            <boxGeometry args={[1.8, 0.06, 0.35]} />
            <meshStandardMaterial color="#0d1117" roughness={0.2} metalness={0.8} />
          </mesh>
          {/* Wing Struts */}
          <mesh position={[0.45, -0.2, 0]} castShadow>
            <boxGeometry args={[0.04, 0.4, 0.12]} />
            <meshStandardMaterial color="#1b2330" />
          </mesh>
          <mesh position={[-0.45, -0.2, 0]} castShadow>
            <boxGeometry args={[0.04, 0.4, 0.12]} />
            <meshStandardMaterial color="#1b2330" />
          </mesh>
        </group>
      )}

      {/* --- WHEELS & BRAKES (4 UNITS) --- */}
      {/* Front Left */}
      <Wheel position={[0.96, 0, 1.4]} radius={wheelRadius} width={wheelWidth} isLeft />
      {/* Front Right */}
      <Wheel position={[-0.96, 0, 1.4]} radius={wheelRadius} width={wheelWidth} isLeft={false} />
      {/* Rear Left */}
      <Wheel position={[0.96, 0, -1.4]} radius={wheelRadius} width={wheelWidth} isLeft />
      {/* Rear Right */}
      <Wheel position={[-0.96, 0, -1.4]} radius={wheelRadius} width={wheelWidth} isLeft={false} />

      {/* --- INTERACTIVE 3D HOTSPOTS --- */}
      {showHotspots &&
        hotspots.map((spot) => {
          const isSelected = selectedHotspot?.id === spot.id;
          return (
            <group key={spot.id} position={spot.position}>
              <Html center distanceFactor={10}>
                <button
                  type="button"
                  onClick={() => onSelectHotspot(spot)}
                  className={`group relative flex items-center justify-center transition-all duration-300 focus:outline-none ${
                    isSelected ? 'scale-125' : 'hover:scale-110'
                  }`}
                  aria-label={spot.title}
                >
                  <span
                    className={`absolute -inset-2 rounded-full animate-ping opacity-60 ${
                      isSelected ? 'bg-cyan-glow' : 'bg-neon-blue'
                    }`}
                  />
                  <span
                    className={`relative flex h-8 w-8 items-center justify-center rounded-full border border-white/60 shadow-lg backdrop-blur-md transition-colors ${
                      isSelected
                        ? 'bg-cyan-500 text-black font-bold'
                        : 'bg-black/75 text-cyan-400 group-hover:bg-cyan-500 group-hover:text-black'
                    }`}
                  >
                    <span className="text-xs">✦</span>
                  </span>
                  {/* Tooltip on hover */}
                  <span className="pointer-events-none absolute left-full ml-2 whitespace-nowrap rounded-md bg-surface-100/95 px-2.5 py-1 text-xs font-medium text-white shadow-xl border border-surface-border opacity-0 group-hover:opacity-100 transition-opacity">
                    {spot.title}
                  </span>
                </button>
              </Html>
            </group>
          );
        })}
    </group>
  );
}

// Subcomponent: Wheel with Tire, Multi-spoke Rim, and Brake Caliper
function Wheel({
  position,
  radius,
  width,
  isLeft,
}: {
  position: [number, number, number];
  radius: number;
  width: number;
  isLeft: boolean;
}) {
  return (
    <group position={position}>
      {/* Rubber Tire (Cylinder rotated on Z axis) */}
      <mesh rotation={[0, 0, Math.PI / 2]} castShadow receiveShadow>
        <cylinderGeometry args={[radius, radius, width, 32]} />
        <meshStandardMaterial color="#1a1c22" roughness={0.85} metalness={0.1} />
      </mesh>

      {/* Rim Face (Forged Alloy) */}
      <mesh
        position={[isLeft ? width * 0.35 : -width * 0.35, 0, 0]}
        rotation={[0, 0, Math.PI / 2]}
      >
        <cylinderGeometry args={[radius * 0.72, radius * 0.72, 0.08, 24]} />
        <meshStandardMaterial color="#cfd6df" metalness={0.9} roughness={0.2} />
      </mesh>

      {/* Inner Brake Rotor (Perforated Steel) */}
      <mesh
        position={[isLeft ? 0.05 : -0.05, 0, 0]}
        rotation={[0, 0, Math.PI / 2]}
      >
        <cylinderGeometry args={[radius * 0.62, radius * 0.62, 0.04, 24]} />
        <meshStandardMaterial color="#737d8c" metalness={0.95} roughness={0.3} />
      </mesh>

      {/* Performance Brake Caliper (Neon Cyan / Racing Red) */}
      <mesh
        position={[isLeft ? 0.08 : -0.08, radius * 0.35, 0]}
        rotation={[0, 0, isLeft ? 0.3 : -0.3]}
      >
        <boxGeometry args={[0.08, radius * 0.4, 0.14]} />
        <meshStandardMaterial color="#00d2ff" roughness={0.25} metalness={0.6} />
      </mesh>
    </group>
  );
}

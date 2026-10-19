'use client';

import React, { useState, useRef, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';
import { Vehicle, Hotspot, PaintColor } from '@/types/vehicle';
import { ProceduralCar } from './ProceduralCar';
import { 
  RotateCw, 
  Eye, 
  Maximize2, 
  Minimize2, 
  Sparkles, 
  Layers, 
  Camera, 
  Sun, 
  Info, 
  X,
  Compass,
  ArrowRight
} from 'lucide-react';

interface VehicleCanvasProps {
  vehicle: Vehicle;
  initialColor?: string;
}

type LightingPreset = 'cyber' | 'showroom' | 'sunset' | 'daylight';
type CameraAngle = 'orbit' | 'front-three-quarter' | 'side' | 'rear-three-quarter' | 'top';

export function VehicleCanvas({ vehicle, initialColor }: VehicleCanvasProps) {
  const [paintColor, setPaintColor] = useState<string>(
    initialColor || vehicle.colorOptions[0]?.hex || '#00d2ff'
  );
  const [lightingPreset, setLightingPreset] = useState<LightingPreset>('cyber');
  const [showHotspots, setShowHotspots] = useState(true);
  const [selectedHotspot, setSelectedHotspot] = useState<Hotspot | null>(null);
  const [autoRotate, setAutoRotate] = useState(true);
  const [wireframe, setWireframe] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [viewMode, setViewMode] = useState<'3d' | 'gallery'>('3d');
  
  const containerRef = useRef<HTMLDivElement>(null);
  const controlsRef = useRef<any>(null);

  // Camera presets
  const handleCameraPreset = (angle: CameraAngle) => {
    if (!controlsRef.current) return;
    setAutoRotate(false);

    switch (angle) {
      case 'front-three-quarter':
        controlsRef.current.setLookAt(2.8, 1.4, 3.8, 0, 0.4, 0, true);
        break;
      case 'side':
        controlsRef.current.setLookAt(5.2, 0.9, 0, 0, 0.4, 0, true);
        break;
      case 'rear-three-quarter':
        controlsRef.current.setLookAt(-3.2, 1.6, -3.8, 0, 0.4, 0, true);
        break;
      case 'top':
        controlsRef.current.setLookAt(0.01, 6.2, 0.01, 0, 0, 0, true);
        break;
      case 'orbit':
      default:
        controlsRef.current.setLookAt(3.8, 1.8, 4.2, 0, 0.4, 0, true);
        break;
    }
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  const hotspots = vehicle.model3DConfig?.hotspots || [];

  return (
    <div
      ref={containerRef}
      className={`relative w-full rounded-2xl overflow-hidden border border-surface-border bg-gradient-to-b from-[#0b0e15] to-[#06080b] shadow-2xl transition-all duration-300 ${
        isFullscreen ? 'h-screen rounded-none' : 'h-[620px] lg:h-[700px]'
      }`}
    >
      {/* 3D Header Controls Banner */}
      <div className="absolute top-4 left-4 right-4 z-20 flex flex-wrap items-center justify-between gap-3 pointer-events-none">
        {/* Model Badge */}
        <div className="pointer-events-auto flex items-center gap-2.5 rounded-full bg-surface-100/80 px-4 py-1.5 backdrop-blur-md border border-white/10 shadow-lg">
          <span className="h-2 w-2 rounded-full bg-cyan-glow animate-pulse" />
          <span className="text-xs font-semibold uppercase tracking-wider text-white">
            3D Interactive Studio
          </span>
          <span className="text-xs text-white/40">|</span>
          <span className="text-xs text-cyan-400 font-mono">
            {vehicle.modelName}
          </span>
        </div>

        {/* View Mode Switcher (3D vs Gallery) & Fullscreen */}
        <div className="pointer-events-auto flex items-center gap-2">
          <div className="flex rounded-lg bg-surface-100/90 p-1 border border-surface-border backdrop-blur-md">
            <button
              type="button"
              onClick={() => setViewMode('3d')}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                viewMode === '3d'
                  ? 'bg-cyan-500 text-black font-semibold'
                  : 'text-white/70 hover:text-white'
              }`}
            >
              3D View
            </button>
            <button
              type="button"
              onClick={() => setViewMode('gallery')}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                viewMode === 'gallery'
                  ? 'bg-cyan-500 text-black font-semibold'
                  : 'text-white/70 hover:text-white'
              }`}
            >
              Photo Gallery
            </button>
          </div>

          <button
            type="button"
            onClick={toggleFullscreen}
            className="rounded-lg bg-surface-100/90 p-2 text-white/80 hover:text-white border border-surface-border backdrop-blur-md transition-colors"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
        </div>
      </div>

      {viewMode === '3d' ? (
        <>
          {/* Main 3D Canvas */}
          <Canvas
            shadows
            camera={{ position: [3.8, 1.8, 4.2], fov: 42 }}
            gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.1 }}
            className="w-full h-full cursor-grab active:cursor-grabbing"
          >
            <Suspense fallback={null}>
              {/* Studio Lighting Engine */}
              {lightingPreset === 'cyber' && (
                <>
                  <ambientLight intensity={0.4} color="#0c1724" />
                  <directionalLight
                    position={[5, 8, 4]}
                    intensity={1.8}
                    color="#e6f7ff"
                    castShadow
                    shadow-mapSize={[2048, 2048]}
                    shadow-bias={-0.0001}
                  />
                  <pointLight position={[-4, 3, -3]} intensity={3.5} color="#00f0ff" />
                  <pointLight position={[3, 2, -4]} intensity={2.0} color="#3b82f6" />
                  <spotLight position={[0, 9, 0]} intensity={1.5} angle={0.6} penumbra={0.8} color="#ffffff" />
                </>
              )}

              {lightingPreset === 'showroom' && (
                <>
                  <ambientLight intensity={0.3} color="#ffffff" />
                  <directionalLight position={[6, 9, 3]} intensity={2.2} color="#ffffff" castShadow />
                  <pointLight position={[-5, 2, 3]} intensity={1.2} color="#ffffff" />
                  <spotLight position={[0, 10, 0]} intensity={2.5} angle={0.5} penumbra={1} color="#ffffff" />
                </>
              )}

              {lightingPreset === 'sunset' && (
                <>
                  <ambientLight intensity={0.4} color="#2b1408" />
                  <directionalLight position={[7, 4, 3]} intensity={3.0} color="#ff9e3b" castShadow />
                  <pointLight position={[-4, 2, -2]} intensity={1.5} color="#ff4d4d" />
                  <pointLight position={[0, 5, -5]} intensity={1.0} color="#ffe58f" />
                </>
              )}

              {lightingPreset === 'daylight' && (
                <>
                  <ambientLight intensity={0.8} color="#f0f6ff" />
                  <directionalLight position={[3, 10, 5]} intensity={2.5} color="#ffffff" castShadow />
                  <directionalLight position={[-3, 8, -5]} intensity={1.0} color="#dbeafe" />
                </>
              )}

              {/* The Procedural 3D Car Model */}
              <ProceduralCar
                color={paintColor}
                wireframe={wireframe}
                modelType={vehicle.model3DConfig?.type || 'sports-coupe'}
                hotspots={hotspots}
                showHotspots={showHotspots}
                selectedHotspot={selectedHotspot}
                onSelectHotspot={(spot) => setSelectedHotspot(spot)}
                autoRotate={autoRotate}
              />

              {/* Reflective Ground Shadow */}
              <ContactShadows
                position={[0, 0, 0]}
                opacity={0.85}
                scale={14}
                blur={1.8}
                far={5}
                resolution={1024}
                color="#000000"
              />

              {/* Studio Stage Pedestal */}
              <mesh position={[0, -0.01, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
                <circleGeometry args={[5.5, 64]} />
                <meshStandardMaterial
                  color="#090c12"
                  roughness={0.4}
                  metalness={0.7}
                />
              </mesh>

              {/* Concentric Decorative Stage Ring */}
              <mesh position={[0, 0.005, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                <ringGeometry args={[4.4, 4.45, 64]} />
                <meshBasicMaterial color="#00f0ff" transparent opacity={0.3} />
              </mesh>

              {/* Drei OrbitControls */}
              <OrbitControls
                ref={controlsRef}
                enableDamping
                dampingFactor={0.06}
                minDistance={2.8}
                maxDistance={9.5}
                maxPolarAngle={Math.PI / 2 - 0.02} // Prevent camera going under floor
                minPolarAngle={0.1}
              />
            </Suspense>
          </Canvas>

          {/* Left Side: Camera Presets & Tools Toolbar */}
          <div className="absolute left-4 bottom-24 lg:bottom-6 z-20 flex flex-col gap-2">
            {/* Turntable Auto-Rotate Toggle */}
            <button
              type="button"
              onClick={() => setAutoRotate(!autoRotate)}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium border backdrop-blur-md transition-all ${
                autoRotate
                  ? 'bg-cyan-500/20 border-cyan-500/60 text-cyan-300'
                  : 'bg-surface-100/80 border-surface-border text-white/70 hover:text-white'
              }`}
              title="Toggle Turntable Rotation"
            >
              <RotateCw size={14} className={autoRotate ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">Turntable</span>
            </button>

            {/* Hotspots Toggle */}
            <button
              type="button"
              onClick={() => setShowHotspots(!showHotspots)}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium border backdrop-blur-md transition-all ${
                showHotspots
                  ? 'bg-cyan-500/20 border-cyan-500/60 text-cyan-300'
                  : 'bg-surface-100/80 border-surface-border text-white/70 hover:text-white'
              }`}
              title="Toggle Feature Hotspots"
            >
              <Sparkles size={14} />
              <span className="hidden sm:inline">Hotspots ({hotspots.length})</span>
            </button>

            {/* Wireframe Mode Toggle */}
            <button
              type="button"
              onClick={() => setWireframe(!wireframe)}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium border backdrop-blur-md transition-all ${
                wireframe
                  ? 'bg-cyan-500/20 border-cyan-500/60 text-cyan-300'
                  : 'bg-surface-100/80 border-surface-border text-white/70 hover:text-white'
              }`}
              title="Toggle Wireframe Shading"
            >
              <Layers size={14} />
              <span className="hidden sm:inline">Wireframe</span>
            </button>

            {/* Camera Angles Menu */}
            <div className="flex items-center gap-1 rounded-lg bg-surface-100/80 p-1 border border-surface-border backdrop-blur-md">
              <button
                type="button"
                onClick={() => handleCameraPreset('front-three-quarter')}
                className="rounded p-1.5 text-xs text-white/70 hover:bg-surface-50 hover:text-white transition-colors"
                title="Front 3/4 View"
              >
                Front
              </button>
              <button
                type="button"
                onClick={() => handleCameraPreset('side')}
                className="rounded p-1.5 text-xs text-white/70 hover:bg-surface-50 hover:text-white transition-colors"
                title="Side Profile"
              >
                Side
              </button>
              <button
                type="button"
                onClick={() => handleCameraPreset('rear-three-quarter')}
                className="rounded p-1.5 text-xs text-white/70 hover:bg-surface-50 hover:text-white transition-colors"
                title="Rear 3/4 View"
              >
                Rear
              </button>
              <button
                type="button"
                onClick={() => handleCameraPreset('top')}
                className="rounded p-1.5 text-xs text-white/70 hover:bg-surface-50 hover:text-white transition-colors"
                title="Top Down"
              >
                Top
              </button>
            </div>
          </div>

          {/* Right Side: Studio Lighting Presets */}
          <div className="absolute right-4 top-20 z-20 flex flex-col gap-1.5 rounded-xl bg-surface-100/80 p-2 border border-surface-border backdrop-blur-md">
            <span className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-white/50">
              Lighting Studio
            </span>
            {(
              [
                { id: 'cyber', label: 'Cyber Studio' },
                { id: 'showroom', label: 'Pure Showroom' },
                { id: 'sunset', label: 'Golden Sunset' },
                { id: 'daylight', label: 'High Noon' },
              ] as const
            ).map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => setLightingPreset(preset.id)}
                className={`flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium text-left transition-colors ${
                  lightingPreset === preset.id
                    ? 'bg-cyan-500/20 text-cyan-300 font-semibold'
                    : 'text-white/60 hover:bg-surface-50 hover:text-white'
                }`}
              >
                <Sun size={12} className={lightingPreset === preset.id ? 'text-cyan-400' : 'text-white/40'} />
                {preset.label}
              </button>
            ))}
          </div>

          {/* Bottom Center: Paint Color Palette Bar */}
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2">
            <div className="flex items-center gap-2.5 rounded-full bg-surface-100/90 px-4 py-2 border border-surface-border backdrop-blur-md shadow-2xl">
              <span className="text-[11px] font-medium text-white/60 pr-1">
                Paint:
              </span>
              {vehicle.colorOptions.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setPaintColor(c.hex)}
                  className={`group relative h-6 w-6 rounded-full transition-transform focus:outline-none ${
                    paintColor === c.hex ? 'scale-125 ring-2 ring-cyan-400 ring-offset-2 ring-offset-black' : 'hover:scale-110'
                  }`}
                  style={{ backgroundColor: c.hex }}
                  title={`${c.name} (${c.finish})`}
                >
                  <span className="pointer-events-none absolute bottom-full mb-2 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-surface-100 px-2 py-0.5 text-[10px] text-white opacity-0 group-hover:opacity-100 transition-opacity border border-surface-border shadow-lg">
                    {c.name}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </>
      ) : (
        /* Fallback High-Resolution Photo Gallery */
        <div className="w-full h-full p-6 flex flex-col justify-between overflow-y-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-12">
            {vehicle.exteriorImages.concat(vehicle.interiorImages).map((img, idx) => (
              <div
                key={idx}
                className="group relative h-56 rounded-xl overflow-hidden border border-surface-border bg-surface-200"
              >
                <img
                  src={img}
                  alt={`${vehicle.modelName} visual ${idx + 1}`}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity p-4 flex items-end">
                  <span className="text-xs text-white font-medium">
                    {idx < vehicle.exteriorImages.length ? 'Exterior View' : 'Interior Cockpit'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Selected Hotspot Details Modal / Drawer */}
      {selectedHotspot && (
        <div className="absolute right-4 bottom-24 lg:bottom-6 z-30 w-80 max-w-[calc(100vw-32px)] rounded-2xl bg-surface-100/95 p-5 border border-cyan-500/40 backdrop-blur-xl shadow-cyan-glow transition-all animate-fadeIn">
          <div className="flex items-start justify-between gap-3 mb-2">
            <div>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-cyan-400">
                {selectedHotspot.category}
              </span>
              <h4 className="text-base font-bold text-white leading-tight">
                {selectedHotspot.title}
              </h4>
            </div>
            <button
              type="button"
              onClick={() => setSelectedHotspot(null)}
              className="rounded-lg p-1 text-white/50 hover:bg-surface-50 hover:text-white transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          <p className="text-xs text-white/75 leading-relaxed mb-3">
            {selectedHotspot.description}
          </p>

          {selectedHotspot.keySpecs && selectedHotspot.keySpecs.length > 0 && (
            <div className="space-y-1.5 border-t border-surface-border pt-2.5">
              {selectedHotspot.keySpecs.map((spec, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-white/50">{spec.label}</span>
                  <span className="font-semibold text-cyan-300 font-mono">{spec.value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

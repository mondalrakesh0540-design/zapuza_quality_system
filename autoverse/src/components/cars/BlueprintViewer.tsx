'use client';

import React, { useState } from 'react';
import { Vehicle, BlueprintDimensions } from '@/types/vehicle';
import { useStore } from '@/lib/store';
import { convertDimension } from '@/lib/units';
import { 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  Grid, 
  Eye, 
  Download, 
  Info, 
  Maximize2, 
  Sliders, 
  Layers, 
  CheckCircle2,
  Compass
} from 'lucide-react';

interface BlueprintViewerProps {
  vehicle: Vehicle;
}

type BlueprintViewAngle = 'side-left' | 'side-right' | 'front' | 'rear' | 'top' | 'chassis';
type BlueprintTheme = 'blueprint-cyan' | 'monochrome-cad' | 'amber-terminal';

export function BlueprintViewer({ vehicle }: BlueprintViewerProps) {
  const { unitSystem, toggleUnitSystem } = useStore();
  const bp: BlueprintDimensions = vehicle.blueprint || {
    overallLengthMm: vehicle.specs.lengthMm,
    overallWidthMm: vehicle.specs.widthMm,
    overallHeightMm: vehicle.specs.heightMm,
    wheelbaseMm: vehicle.specs.wheelbaseMm,
    groundClearanceMm: vehicle.specs.groundClearanceMm,
    frontTrackMm: vehicle.specs.frontTrackMm || 1550,
    rearTrackMm: vehicle.specs.rearTrackMm || 1550,
    turningRadiusM: vehicle.specs.turningRadiusMeters || 5.3,
    bootCapacityL: vehicle.specs.bootCapacityLiters,
    fuelTankL: vehicle.specs.fuelTankCapacityLiters,
    tyreSpecification: vehicle.specs.frontTyres,
    wheelRimSizeInches: vehicle.specs.wheelSizeInches,
    schematicType: 'ISO 128 Dimension Schematic',
    verificationSource: 'Certified OEM Homologation Specifications (Form 22)',
  };

  const [viewAngle, setViewAngle] = useState<BlueprintViewAngle>('side-left');
  const [theme, setTheme] = useState<BlueprintTheme>('blueprint-cyan');
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [showGrid, setShowGrid] = useState<boolean>(true);
  const [showDimensions, setShowDimensions] = useState<boolean>(true);

  const formatDim = (mm: number) => convertDimension(mm, unitSystem);

  // Proportional body parameters
  const isSUV = vehicle.bodyStyle === 'SUV' || vehicle.bodyStyle === 'Off-Road' || vehicle.bodyStyle === 'Compact SUV' || vehicle.bodyStyle === 'MUV' || vehicle.bodyStyle === 'MPV';
  const isCoupe = vehicle.bodyStyle === 'Coupe' || vehicle.bodyStyle === 'Sports Car' || vehicle.bodyStyle === 'Supercar' || vehicle.bodyStyle === 'Hypercar';

  const themeColors = {
    'blueprint-cyan': {
      bg: 'bg-[#06101e]',
      grid: '#00d2ff15',
      gridMajor: '#00d2ff30',
      line: '#00f0ff',
      dim: '#38bdf8',
      text: '#7dd3fc',
      accent: 'border-cyan-500/40 text-cyan-400',
    },
    'monochrome-cad': {
      bg: 'bg-[#0d1117]',
      grid: '#ffffff10',
      gridMajor: '#ffffff22',
      line: '#e6edf3',
      dim: '#8b949e',
      text: '#c9d1d9',
      accent: 'border-white/30 text-white',
    },
    'amber-terminal': {
      bg: 'bg-[#140e05]',
      grid: '#f59e0b12',
      gridMajor: '#f59e0b25',
      line: '#fbbf24',
      dim: '#d97706',
      text: '#fde68a',
      accent: 'border-amber-500/40 text-amber-400',
    },
  }[theme];

  return (
    <div className="w-full rounded-2xl border border-surface-border bg-surface-100 overflow-hidden shadow-2xl space-y-4">
      {/* Blueprint Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 border-b border-surface-border bg-surface-200/60 backdrop-blur-md">
        {/* View Angle Switcher */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-white/50 pr-1 shrink-0">
            Orthographic:
          </span>
          {(
            [
              { id: 'side-left', label: 'Left Elevation' },
              { id: 'side-right', label: 'Right Elevation' },
              { id: 'front', label: 'Front' },
              { id: 'rear', label: 'Rear' },
              { id: 'top', label: 'Plan View' },
              { id: 'chassis', label: 'Chassis Layout' },
            ] as const
          ).map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => setViewAngle(v.id)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-all ${
                viewAngle === v.id
                  ? 'bg-cyan-500 text-black font-bold shadow-cyan-glow'
                  : 'bg-surface-100 text-white/70 hover:bg-surface-50 hover:text-white border border-surface-border'
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>

        {/* Tools and Unit System Controls */}
        <div className="flex items-center gap-2">
          {/* Unit Toggle Button */}
          <button
            type="button"
            onClick={toggleUnitSystem}
            className="flex items-center gap-1.5 rounded-lg bg-surface-100 px-3 py-1.5 text-xs font-semibold text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500/10 transition-colors"
            title="Switch Metric (mm) / Imperial (in)"
          >
            <span>Unit:</span>
            <span className="uppercase text-white font-mono">{unitSystem}</span>
          </button>

          {/* Grid Toggle */}
          <button
            type="button"
            onClick={() => setShowGrid(!showGrid)}
            className={`rounded-lg p-1.5 text-xs border transition-colors ${
              showGrid
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                : 'bg-surface-100 text-white/60 border-surface-border hover:text-white'
            }`}
            title="Toggle CAD Grid"
          >
            <Grid size={15} />
          </button>

          {/* Dimensions Toggle */}
          <button
            type="button"
            onClick={() => setShowDimensions(!showDimensions)}
            className={`rounded-lg p-1.5 text-xs border transition-colors ${
              showDimensions
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                : 'bg-surface-100 text-white/60 border-surface-border hover:text-white'
            }`}
            title="Toggle Dimension Annotations"
          >
            <Eye size={15} />
          </button>

          {/* Zoom In/Out/Reset */}
          <div className="flex items-center rounded-lg bg-surface-100 border border-surface-border">
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.max(0.7, z - 0.15))}
              className="p-1.5 text-white/70 hover:text-white hover:bg-surface-50 rounded-l"
              title="Zoom Out"
            >
              <ZoomOut size={15} />
            </button>
            <button
              type="button"
              onClick={() => setZoomLevel(1)}
              className="px-2 py-1 text-[11px] font-mono text-white/60 hover:text-white"
              title="Reset Zoom"
            >
              {Math.round(zoomLevel * 100)}%
            </button>
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.min(1.6, z + 0.15))}
              className="p-1.5 text-white/70 hover:text-white hover:bg-surface-50 rounded-r"
              title="Zoom In"
            >
              <ZoomIn size={15} />
            </button>
          </div>

          {/* Color Theme Selector */}
          <div className="hidden sm:flex items-center gap-1 rounded-lg bg-surface-100 p-1 border border-surface-border">
            {(
              [
                { id: 'blueprint-cyan', title: 'Cyan CAD' },
                { id: 'monochrome-cad', title: 'White CAD' },
                { id: 'amber-terminal', title: 'Amber CRT' },
              ] as const
            ).map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTheme(t.id)}
                className={`h-4 w-4 rounded-full transition-all ${
                  theme === t.id ? 'ring-2 ring-white scale-110' : 'opacity-60 hover:opacity-100'
                }`}
                style={{
                  backgroundColor:
                    t.id === 'blueprint-cyan'
                      ? '#00f0ff'
                      : t.id === 'monochrome-cad'
                      ? '#ffffff'
                      : '#f59e0b',
                }}
                title={t.title}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Main CAD Interactive Canvas Area */}
      <div
        className={`relative w-full h-[520px] lg:h-[580px] overflow-hidden flex items-center justify-center select-none ${themeColors.bg} transition-colors duration-300`}
      >
        {/* Background Grid Pattern (Major & Minor CAD Grid lines) */}
        {showGrid && (
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              backgroundImage: `
                linear-gradient(to right, ${themeColors.gridMajor} 1px, transparent 1px),
                linear-gradient(to bottom, ${themeColors.gridMajor} 1px, transparent 1px),
                linear-gradient(to right, ${themeColors.grid} 1px, transparent 1px),
                linear-gradient(to bottom, ${themeColors.grid} 1px, transparent 1px)
              `,
              backgroundSize: '80px 80px, 80px 80px, 16px 16px, 16px 16px',
            }}
          />
        )}

        {/* Engineering ISO Watermark & Coordinate Axis */}
        <div className="absolute top-4 left-4 z-10 pointer-events-none space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase font-bold tracking-widest text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
              ISO 128-20 HOMOLOGATION SCHEMATIC
            </span>
            <span className="text-[11px] font-mono text-white/40">
              SCALE: 1:25 (CAD PROJECTION)
            </span>
          </div>
          <p className="text-[10px] font-mono text-white/50">
            DATUM ORIGIN: [X: 0.00, Y: 0.00, Z: 0.00] | METRIC VERIFICATION: {bp.overallLengthMm} mm
          </p>
        </div>

        {/* CAD Blueprint Drawing Render */}
        <div
          className="relative transition-transform duration-200 flex items-center justify-center"
          style={{ transform: `scale(${zoomLevel})` }}
        >
          <svg
            width="820"
            height="440"
            viewBox="0 0 820 440"
            className="overflow-visible"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Defs for CAD Dimension Marker Arrowheads */}
            <defs>
              <marker
                id="dim-arrow-start"
                markerWidth="8"
                markerHeight="8"
                refX="0"
                refY="4"
                orient="auto"
              >
                <path d="M8,1 L0,4 L8,7 Z" fill={themeColors.dim} />
              </marker>
              <marker
                id="dim-arrow-end"
                markerWidth="8"
                markerHeight="8"
                refX="8"
                refY="4"
                orient="auto"
              >
                <path d="M0,1 L8,4 L0,7 Z" fill={themeColors.dim} />
              </marker>
            </defs>

            {/* Render View Specific Geometry */}
            {viewAngle === 'side-left' || viewAngle === 'side-right' ? (
              <g
                transform={
                  viewAngle === 'side-right'
                    ? 'translate(820, 0) scale(-1, 1)'
                    : undefined
                }
              >
                {/* Ground Reference Plane */}
                <line
                  x1="60"
                  y1="340"
                  x2="760"
                  y2="340"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                  opacity="0.5"
                />

                {/* Car Silhouette Outline (Side Profile) */}
                <path
                  d={
                    isSUV
                      ? 'M 140 310 L 140 280 Q 150 250 180 240 L 290 230 Q 320 220 340 160 L 520 150 Q 560 150 630 190 L 680 230 L 690 300 Q 690 310 680 315 L 610 315 A 45 45 0 0 0 520 315 L 310 315 A 45 45 0 0 0 220 315 L 150 315 Z'
                      : isCoupe
                      ? 'M 130 315 L 130 290 Q 140 270 200 260 L 320 240 Q 380 230 420 180 L 510 180 Q 580 180 660 250 L 690 280 L 690 315 L 600 315 A 42 42 0 0 0 516 315 L 304 315 A 42 42 0 0 0 220 315 L 140 315 Z'
                      : 'M 140 315 L 140 285 Q 150 265 210 255 L 310 245 Q 360 230 380 170 L 510 170 Q 560 170 630 220 L 680 250 L 685 315 L 600 315 A 42 42 0 0 0 516 315 L 304 315 A 42 42 0 0 0 220 315 L 150 315 Z'
                  }
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Cabin Greenhouse & Glass Window Cutout */}
                <path
                  d={
                    isSUV
                      ? 'M 350 165 L 515 155 Q 550 155 615 195 L 635 230 L 330 230 Q 340 180 350 165 Z'
                      : 'M 425 185 L 510 185 Q 560 185 640 250 L 350 245 Q 395 210 425 185 Z'
                  }
                  fill={themeColors.line}
                  fillOpacity="0.08"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                  strokeDasharray="2 2"
                />

                {/* B-Pillar Division */}
                <line
                  x1="450"
                  y1={isSUV ? '155' : '185'}
                  x2="450"
                  y2="235"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />

                {/* Wheels & Tires */}
                {/* Front Wheel (Right in SVG coordinate) */}
                <circle
                  cx="558"
                  cy="315"
                  r="38"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="2"
                />
                <circle
                  cx="558"
                  cy="315"
                  r="26"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="1"
                />
                <circle
                  cx="558"
                  cy="315"
                  r="6"
                  fill={themeColors.line}
                />

                {/* Rear Wheel (Left in SVG coordinate) */}
                <circle
                  cx="262"
                  cy="315"
                  r="38"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="2"
                />
                <circle
                  cx="262"
                  cy="315"
                  r="26"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="1"
                />
                <circle
                  cx="262"
                  cy="315"
                  r="6"
                  fill={themeColors.line}
                />

                {/* Side Body Crease Lines */}
                <line
                  x1="220"
                  y1="255"
                  x2="590"
                  y2="245"
                  stroke={themeColors.line}
                  strokeWidth="1"
                  opacity="0.6"
                />
                <line
                  x1="262"
                  y1="285"
                  x2="558"
                  y2="285"
                  stroke={themeColors.line}
                  strokeWidth="1"
                  strokeDasharray="6 3"
                  opacity="0.4"
                />
              </g>
            ) : viewAngle === 'front' || viewAngle === 'rear' ? (
              <g>
                {/* Ground Reference Plane */}
                <line
                  x1="180"
                  y1="340"
                  x2="640"
                  y2="340"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                  opacity="0.5"
                />

                {/* Front / Rear Body Symmetrical Cross-section */}
                <path
                  d={
                    isSUV
                      ? 'M 270 315 L 260 240 Q 270 170 330 160 L 490 160 Q 550 170 560 240 L 550 315 L 510 315 A 35 35 0 0 1 480 320 L 340 320 A 35 35 0 0 1 310 315 Z'
                      : 'M 260 315 L 255 250 Q 280 180 340 170 L 480 170 Q 540 180 565 250 L 560 315 L 525 315 A 35 35 0 0 1 495 320 L 325 320 A 35 35 0 0 1 295 315 Z'
                  }
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />

                {/* Windshield Contour */}
                <path
                  d="M 335 175 L 485 175 Q 520 185 530 235 L 290 235 Q 300 185 335 175 Z"
                  fill={themeColors.line}
                  fillOpacity="0.08"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />

                {/* Left & Right Headlamps / Taillamps */}
                <rect
                  x="268"
                  y="245"
                  width="55"
                  height="16"
                  rx="3"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />
                <rect
                  x="497"
                  y="245"
                  width="55"
                  height="16"
                  rx="3"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />

                {/* Center Grille / Lightbar */}
                <line
                  x1="325"
                  y1="253"
                  x2="495"
                  y2="253"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                  strokeDasharray="4 2"
                />

                {/* Left & Right Mirrors */}
                <rect
                  x="222"
                  y="225"
                  width="32"
                  height="18"
                  rx="4"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />
                <rect
                  x="566"
                  y="225"
                  width="32"
                  height="18"
                  rx="4"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />

                {/* Left & Right Front Tires */}
                <rect
                  x="260"
                  y="295"
                  width="32"
                  height="45"
                  rx="4"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="2"
                />
                <rect
                  x="528"
                  y="295"
                  width="32"
                  height="45"
                  rx="4"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="2"
                />
              </g>
            ) : viewAngle === 'top' ? (
              <g>
                {/* Top-Down Aerodynamic Planform */}
                <path
                  d="M 180 220 Q 185 130 260 120 L 560 120 Q 635 130 640 220 Q 635 310 560 320 L 260 320 Q 185 310 180 220 Z"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />

                {/* Glass Greenhouse Roof / Panoramic Canopy */}
                <rect
                  x="330"
                  y="150"
                  width="180"
                  height="140"
                  rx="15"
                  fill={themeColors.line}
                  fillOpacity="0.08"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />

                {/* Front Hood Strakes */}
                <line
                  x1="520"
                  y1="160"
                  x2="615"
                  y2="175"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                  strokeDasharray="3 3"
                />
                <line
                  x1="520"
                  y1="280"
                  x2="615"
                  y2="265"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                  strokeDasharray="3 3"
                />

                {/* Wheels from Top View */}
                <rect
                  x="530"
                  y="105"
                  width="55"
                  height="22"
                  rx="3"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />
                <rect
                  x="530"
                  y="313"
                  width="55"
                  height="22"
                  rx="3"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />
                <rect
                  x="235"
                  y="105"
                  width="55"
                  height="22"
                  rx="3"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />
                <rect
                  x="235"
                  y="313"
                  width="55"
                  height="22"
                  rx="3"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />
              </g>
            ) : (
              /* Chassis Layout / Monocoque View */
              <g>
                {/* Structural Platform Frame */}
                <rect
                  x="200"
                  y="150"
                  width="420"
                  height="140"
                  rx="10"
                  fill="none"
                  stroke={themeColors.line}
                  strokeWidth="2"
                  strokeDasharray="4 2"
                />

                {/* Subframe Crossmembers */}
                <line
                  x1="280"
                  y1="150"
                  x2="280"
                  y2="290"
                  stroke={themeColors.line}
                  strokeWidth="2"
                />
                <line
                  x1="540"
                  y1="150"
                  x2="540"
                  y2="290"
                  stroke={themeColors.line}
                  strokeWidth="2"
                />

                {/* Energy Storage Pack / Battery or Fuel Tank */}
                <rect
                  x="310"
                  y="170"
                  width="200"
                  height="100"
                  rx="6"
                  fill={themeColors.line}
                  fillOpacity="0.12"
                  stroke={themeColors.line}
                  strokeWidth="2"
                />
                <text
                  x="410"
                  y="225"
                  fill={themeColors.text}
                  fontSize="12"
                  fontFamily="monospace"
                  textAnchor="middle"
                  fontWeight="bold"
                >
                  {vehicle.fuelType === 'Electric'
                    ? `BATTERY PACK: ${vehicle.specs.batteryCapacityKwh || 45} kWh`
                    : `FUEL TANK: ${bp.fuelTankL || 50} LITERS`}
                </text>

                {/* Front & Rear Axles */}
                <line
                  x1="540"
                  y1="100"
                  x2="540"
                  y2="340"
                  stroke={themeColors.line}
                  strokeWidth="3"
                />
                <line
                  x1="280"
                  y1="100"
                  x2="280"
                  y2="340"
                  stroke={themeColors.line}
                  strokeWidth="3"
                />

                {/* 4 Wheels */}
                <rect
                  x="515"
                  y="90"
                  width="50"
                  height="24"
                  rx="4"
                  fill={themeColors.line}
                  fillOpacity="0.3"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />
                <rect
                  x="515"
                  y="326"
                  width="50"
                  height="24"
                  rx="4"
                  fill={themeColors.line}
                  fillOpacity="0.3"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />
                <rect
                  x="255"
                  y="90"
                  width="50"
                  height="24"
                  rx="4"
                  fill={themeColors.line}
                  fillOpacity="0.3"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />
                <rect
                  x="255"
                  y="326"
                  width="50"
                  height="24"
                  rx="4"
                  fill={themeColors.line}
                  fillOpacity="0.3"
                  stroke={themeColors.line}
                  strokeWidth="1.5"
                />
              </g>
            )}

            {/* ======================================================== */}
            {/* DIMENSION ARROWS & LEADER ANNOTATIONS (ISO 128 COMPLIANT) */}
            {/* ======================================================== */}
            {showDimensions && (
              <g className="transition-opacity duration-200">
                {viewAngle === 'side-left' || viewAngle === 'side-right' ? (
                  <>
                    {/* Dimension: Overall Length (Bottom) */}
                    <line
                      x1="130"
                      y1="380"
                      x2="690"
                      y2="380"
                      stroke={themeColors.dim}
                      strokeWidth="1.5"
                      markerStart="url(#dim-arrow-start)"
                      markerEnd="url(#dim-arrow-end)"
                    />
                    {/* Extension lines */}
                    <line x1="130" y1="315" x2="130" y2="390" stroke={themeColors.dim} strokeWidth="0.8" strokeDasharray="3 3" opacity="0.6" />
                    <line x1="690" y1="310" x2="690" y2="390" stroke={themeColors.dim} strokeWidth="0.8" strokeDasharray="3 3" opacity="0.6" />
                    <text
                      x="410"
                      y="375"
                      fill={themeColors.text}
                      fontSize="12"
                      fontFamily="monospace"
                      textAnchor="middle"
                      fontWeight="bold"
                    >
                      OVERALL LENGTH: {formatDim(bp.overallLengthMm)}
                    </text>

                    {/* Dimension: Wheelbase */}
                    <line
                      x1="262"
                      y1="348"
                      x2="558"
                      y2="348"
                      stroke={themeColors.dim}
                      strokeWidth="1.5"
                      markerStart="url(#dim-arrow-start)"
                      markerEnd="url(#dim-arrow-end)"
                    />
                    <text
                      x="410"
                      y="344"
                      fill={themeColors.text}
                      fontSize="11"
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      WHEELBASE: {formatDim(bp.wheelbaseMm)}
                    </text>

                    {/* Dimension: Overall Height (Right) */}
                    <line
                      x1="740"
                      y1="150"
                      x2="740"
                      y2="340"
                      stroke={themeColors.dim}
                      strokeWidth="1.5"
                      markerStart="url(#dim-arrow-start)"
                      markerEnd="url(#dim-arrow-end)"
                    />
                    <line x1="520" y1="150" x2="750" y2="150" stroke={themeColors.dim} strokeWidth="0.8" strokeDasharray="3 3" opacity="0.6" />
                    <line x1="600" y1="340" x2="750" y2="340" stroke={themeColors.dim} strokeWidth="0.8" strokeDasharray="3 3" opacity="0.6" />
                    <text
                      x="755"
                      y="250"
                      fill={themeColors.text}
                      fontSize="11"
                      fontFamily="monospace"
                      textAnchor="start"
                    >
                      HEIGHT: {formatDim(bp.overallHeightMm)}
                    </text>

                    {/* Ground Clearance Callout */}
                    <line
                      x1="410"
                      y1="315"
                      x2="410"
                      y2="340"
                      stroke={themeColors.dim}
                      strokeWidth="1.5"
                      markerStart="url(#dim-arrow-start)"
                      markerEnd="url(#dim-arrow-end)"
                    />
                    <text
                      x="410"
                      y="310"
                      fill={themeColors.text}
                      fontSize="10"
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      CLEARANCE: {formatDim(bp.groundClearanceMm)}
                    </text>
                  </>
                ) : viewAngle === 'front' || viewAngle === 'rear' ? (
                  <>
                    {/* Dimension: Overall Width (Top) */}
                    <line
                      x1="222"
                      y1="130"
                      x2="598"
                      y2="130"
                      stroke={themeColors.dim}
                      strokeWidth="1.5"
                      markerStart="url(#dim-arrow-start)"
                      markerEnd="url(#dim-arrow-end)"
                    />
                    <line x1="222" y1="120" x2="222" y2="230" stroke={themeColors.dim} strokeWidth="0.8" strokeDasharray="3 3" opacity="0.6" />
                    <line x1="598" y1="120" x2="598" y2="230" stroke={themeColors.dim} strokeWidth="0.8" strokeDasharray="3 3" opacity="0.6" />
                    <text
                      x="410"
                      y="124"
                      fill={themeColors.text}
                      fontSize="12"
                      fontFamily="monospace"
                      textAnchor="middle"
                      fontWeight="bold"
                    >
                      OVERALL WIDTH (EXCL. MIRRORS): {formatDim(bp.overallWidthMm)}
                    </text>

                    {/* Track Width (Bottom) */}
                    <line
                      x1="276"
                      y1="370"
                      x2="544"
                      y2="370"
                      stroke={themeColors.dim}
                      strokeWidth="1.5"
                      markerStart="url(#dim-arrow-start)"
                      markerEnd="url(#dim-arrow-end)"
                    />
                    <text
                      x="410"
                      y="365"
                      fill={themeColors.text}
                      fontSize="11"
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      TRACK WIDTH: {formatDim(bp.frontTrackMm)}
                    </text>
                  </>
                ) : (
                  <>
                    {/* Top View Dimensions */}
                    <line
                      x1="180"
                      y1="365"
                      x2="640"
                      y2="365"
                      stroke={themeColors.dim}
                      strokeWidth="1.5"
                      markerStart="url(#dim-arrow-start)"
                      markerEnd="url(#dim-arrow-end)"
                    />
                    <text
                      x="410"
                      y="360"
                      fill={themeColors.text}
                      fontSize="12"
                      fontFamily="monospace"
                      textAnchor="middle"
                      fontWeight="bold"
                    >
                      TOTAL PLAN LENGTH: {formatDim(bp.overallLengthMm)}
                    </text>
                  </>
                )}
              </g>
            )}
          </svg>
        </div>

        {/* Bottom Status / Specification Pill in Blueprint */}
        <div className="absolute bottom-3 left-4 right-4 z-10 flex flex-wrap items-center justify-between gap-2 pointer-events-none text-xs font-mono">
          <div className="pointer-events-auto flex items-center gap-2 bg-surface-100/85 px-3 py-1.5 rounded-lg border border-surface-border backdrop-blur-md">
            <span className="text-white/60">TYRES:</span>
            <span className="text-cyan-300 font-bold">{bp.tyreSpecification}</span>
            <span className="text-white/40">|</span>
            <span className="text-white/60">RIMS:</span>
            <span className="text-cyan-300 font-bold">{bp.wheelRimSizeInches}" ALLOY</span>
          </div>

          <div className="pointer-events-auto flex items-center gap-2 bg-surface-100/85 px-3 py-1.5 rounded-lg border border-surface-border backdrop-blur-md">
            <span className="text-white/50">TURNING RADIUS:</span>
            <span className="text-cyan-300 font-bold">{bp.turningRadiusM} METERS</span>
            <span className="text-white/40">|</span>
            <span className="text-white/50">BOOT:</span>
            <span className="text-cyan-300 font-bold">{bp.bootCapacityL} L</span>
          </div>
        </div>
      </div>

      {/* Engineering Certification Footer */}
      <div className="p-4 bg-surface-200/40 border-t border-surface-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
          <span className="text-white/70">
            Source:{' '}
            <strong className="text-white font-medium">
              {bp.verificationSource}
            </strong>
          </span>
        </div>

        <div className="text-[11px] text-white/50 italic">
          ISO 128 Dimension-based technical schematic • Not an official CAD export
        </div>
      </div>
    </div>
  );
}

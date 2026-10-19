'use client';

import React, { useState } from 'react';
import { Vehicle, VehicleComponent } from '@/types/vehicle';
import { getComponentsForVehicle } from '@/data/components';
import { 
  Cpu, 
  BatteryCharging, 
  Zap, 
  Disc, 
  Layers, 
  Settings2, 
  ShieldCheck, 
  AlertCircle, 
  Wrench, 
  Search, 
  ArrowRight, 
  CheckCircle2, 
  Sliders,
  Sparkles,
  Info
} from 'lucide-react';

interface PartsExplorerProps {
  vehicle: Vehicle;
}

export function PartsExplorer({ vehicle }: PartsExplorerProps) {
  const componentsList = vehicle.components && vehicle.components.length > 0 
    ? vehicle.components 
    : getComponentsForVehicle(vehicle.id);

  const [selectedComponent, setSelectedComponent] = useState<VehicleComponent>(
    componentsList[0] || null
  );
  const [filterSystem, setFilterSystem] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Extract distinct systems
  const allSystems = [
    'All',
    ...Array.from(new Set(componentsList.map((c) => c.system))),
  ];

  const filteredComponents = componentsList.filter((comp) => {
    const matchesSystem = filterSystem === 'All' || comp.system === filterSystem;
    const matchesSearch =
      comp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      comp.subsystem.toLowerCase().includes(searchQuery.toLowerCase()) ||
      comp.operatingPrinciple.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSystem && matchesSearch;
  });

  return (
    <div className="w-full rounded-2xl border border-surface-border bg-surface-100 overflow-hidden shadow-2xl space-y-4">
      {/* Header and System Categories Bar */}
      <div className="p-4 border-b border-surface-border bg-surface-200/50 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
              <h3 className="text-base font-bold text-white tracking-wide">
                Interactive Vehicle Engineering & Parts Explorer
              </h3>
            </div>
            <p className="text-xs text-white/60">
              Explore key powertrain, chassis, battery, suspension, and brake subsystems for {vehicle.brandName} {vehicle.modelName}.
            </p>
          </div>

          {/* Search Input */}
          <div className="relative w-full sm:w-64">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
            <input
              type="text"
              placeholder="Filter components..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg bg-surface-100 py-1.5 pl-9 pr-3 text-xs text-white placeholder-white/40 border border-surface-border focus:border-cyan-500 focus:outline-none"
            />
          </div>
        </div>

        {/* System Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
          {allSystems.map((sys) => (
            <button
              key={sys}
              type="button"
              onClick={() => setFilterSystem(sys)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors ${
                filterSystem === sys
                  ? 'bg-cyan-500 text-black font-semibold'
                  : 'bg-surface-100 text-white/70 hover:bg-surface-50 hover:text-white border border-surface-border'
              }`}
            >
              {sys}
            </button>
          ))}
        </div>
      </div>

      {/* Main Split Grid: Parts Directory (Left) + Detailed Technical Inspector (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 p-4 pt-0">
        {/* Left Column: Subsystem Cards List (4 Cols) */}
        <div className="lg:col-span-4 space-y-2.5 max-h-[580px] overflow-y-auto pr-1">
          {filteredComponents.length > 0 ? (
            filteredComponents.map((comp) => {
              const isSelected = selectedComponent?.id === comp.id;
              return (
                <button
                  key={comp.id}
                  type="button"
                  onClick={() => setSelectedComponent(comp)}
                  className={`w-full text-left rounded-xl p-3.5 border transition-all duration-200 ${
                    isSelected
                      ? 'bg-cyan-950/40 border-cyan-500/70 shadow-cyan-glow'
                      : 'bg-surface-200/40 border-surface-border hover:bg-surface-50 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-cyan-400">
                      {comp.system}
                    </span>
                    {comp.isVerifiedOem ? (
                      <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-medium text-emerald-400 border border-emerald-500/20">
                        OEM Verified
                      </span>
                    ) : (
                      <span className="rounded bg-white/5 px-1.5 py-0.5 text-[9px] font-medium text-white/50">
                        Reference
                      </span>
                    )}
                  </div>

                  <h4 className="text-sm font-bold text-white group-hover:text-cyan-300">
                    {comp.name}
                  </h4>

                  <p className="text-xs text-white/60 line-clamp-2 mt-1 leading-relaxed">
                    {comp.operatingPrinciple}
                  </p>

                  <div className="mt-2.5 flex items-center justify-between text-[11px] text-white/40 border-t border-white/5 pt-2">
                    <span>{comp.subsystem}</span>
                    <span className="text-cyan-400 group-hover:translate-x-1 transition-transform">
                      Inspect &rarr;
                    </span>
                  </div>
                </button>
              );
            })
          ) : (
            <div className="p-8 text-center text-xs text-white/50 border border-dashed border-surface-border rounded-xl">
              No matching components found for "{searchQuery}".
            </div>
          )}
        </div>

        {/* Right Column: Active Component Deep-Dive Inspection (8 Cols) */}
        <div className="lg:col-span-8">
          {selectedComponent ? (
            <div className="rounded-xl border border-surface-border bg-surface-200/50 p-5 space-y-6">
              {/* Component Header */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-surface-border pb-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-cyan-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-cyan-300 border border-cyan-500/30">
                      {selectedComponent.system}
                    </span>
                    <span className="text-xs text-white/40">•</span>
                    <span className="text-xs font-medium text-white/70">
                      {selectedComponent.subsystem}
                    </span>
                  </div>

                  <h2 className="text-xl sm:text-2xl font-extrabold text-white">
                    {selectedComponent.name}
                  </h2>

                  {selectedComponent.supplierOrOem && (
                    <p className="text-xs text-cyan-400 font-mono">
                      OEM / Engineering Origin: {selectedComponent.supplierOrOem}
                    </p>
                  )}
                </div>

                <div className="shrink-0">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-100 px-3 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/30">
                    <CheckCircle2 size={13} />
                    <span>{selectedComponent.isVerifiedOem ? 'Verified Architecture' : 'Educational Schematic'}</span>
                  </span>
                </div>
              </div>

              {/* Operating Principle / Engineering Description */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-white/50">
                  Operating Principle & Architecture
                </h4>
                <p className="text-sm text-white/85 leading-relaxed bg-surface-100/60 p-4 rounded-xl border border-surface-border">
                  {selectedComponent.operatingPrinciple}
                </p>
              </div>

              {/* Technical Specifications Matrix */}
              {selectedComponent.technicalSpecs && selectedComponent.technicalSpecs.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-white/50">
                    Engineering Specifications
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {selectedComponent.technicalSpecs.map((spec, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between rounded-lg bg-surface-100/80 px-3.5 py-2.5 border border-surface-border"
                      >
                        <span className="text-xs text-white/60">{spec.label}</span>
                        <span className="text-xs font-bold font-mono text-cyan-300">
                          {spec.value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Diagram / Schematic Visualizer Area */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-white/50">
                  Engineering Schematic & Circuit
                </h4>
                <div className="relative rounded-xl border border-cyan-500/30 bg-[#070d18] p-5 overflow-hidden">
                  <div className="flex items-center gap-2 mb-3">
                    <Layers size={14} className="text-cyan-400" />
                    <span className="text-xs font-bold text-white tracking-wide">
                      {selectedComponent.name} — Technical Architecture Diagram
                    </span>
                  </div>

                  {/* High-Tech Circuit Graphic */}
                  <div className="h-44 w-full rounded-lg bg-surface-100/40 border border-surface-border flex flex-col items-center justify-center p-4 text-center relative overflow-hidden">
                    {/* SVG Graphic Representation */}
                    <svg className="w-full h-full max-h-36" viewBox="0 0 400 120" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <rect x="20" y="25" width="100" height="70" rx="8" stroke="#00f0ff" strokeWidth="2" fill="#00f0ff10" />
                      <text x="70" y="65" fill="#00f0ff" fontSize="10" fontFamily="monospace" textAnchor="middle" fontWeight="bold">INPUT</text>
                      
                      <line x1="120" y1="60" x2="160" y2="60" stroke="#00f0ff" strokeWidth="2" strokeDasharray="4 2" />
                      
                      <rect x="160" y="15" width="120" height="90" rx="8" stroke="#38bdf8" strokeWidth="2.5" fill="#38bdf815" />
                      <text x="220" y="55" fill="#ffffff" fontSize="11" fontFamily="sans-serif" textAnchor="middle" fontWeight="bold">{selectedComponent.subsystem}</text>
                      <text x="220" y="75" fill="#38bdf8" fontSize="9" fontFamily="monospace" textAnchor="middle">CORE UNIT</text>
                      
                      <line x1="280" y1="60" x2="320" y2="60" stroke="#00f0ff" strokeWidth="2" strokeDasharray="4 2" />
                      
                      <rect x="320" y="25" width="60" height="70" rx="8" stroke="#00f0ff" strokeWidth="2" fill="#00f0ff10" />
                      <text x="350" y="65" fill="#00f0ff" fontSize="10" fontFamily="monospace" textAnchor="middle" fontWeight="bold">WHEELS</text>
                    </svg>

                    <p className="text-xs text-white/70 italic mt-2 max-w-xl">
                      {selectedComponent.diagramDescription}
                    </p>
                  </div>
                </div>
              </div>

              {/* Maintenance Lifecycle & Service Advice */}
              <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 p-4 flex items-start gap-3">
                <Wrench size={18} className="text-amber-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h5 className="text-xs font-bold text-amber-300 uppercase tracking-wide">
                    Maintenance Lifecycle & Inspection Schedule
                  </h5>
                  <p className="text-xs text-amber-100/80 leading-relaxed">
                    {selectedComponent.maintenanceLifecycle}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-12 text-center text-sm text-white/40 border border-surface-border rounded-xl">
              Select a component from the list on the left to inspect its engineering specifications.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

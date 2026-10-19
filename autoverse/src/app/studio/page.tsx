'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { VEHICLES } from '@/data/vehicles';
import { Vehicle } from '@/types/vehicle';
import { VehicleCanvas } from '@/components/3d/VehicleCanvas';
import { Sparkles, ArrowRight, ShieldCheck, Car, ExternalLink } from 'lucide-react';

export default function StudioPage() {
  const [selectedVehicle, setSelectedVehicle] = useState<Vehicle>(VEHICLES[0]);

  const carsWith3D = VEHICLES.filter(v => v.has3D);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-surface-border pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
            <Sparkles size={14} />
            <span>Interactive WebGL 3D Showroom</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white font-display mt-1">
            3D Vehicle Studio
          </h1>
          <p className="text-sm text-white/60 mt-1">
            Real-time procedural 3D models with PBR materials, custom studio lighting, and interactive component hotspots.
          </p>
        </div>

        {/* View Profile Link */}
        <Link
          href={`/cars/${selectedVehicle.slug}`}
          className="flex items-center gap-2 rounded-xl bg-surface-100 px-4 py-2 text-xs font-semibold text-white border border-surface-border hover:bg-surface-50 self-start md:self-auto"
        >
          <span>View Full Specifications</span>
          <ArrowRight size={13} />
        </Link>
      </div>

      {/* Model Selector Bar */}
      <div className="space-y-2">
        <span className="text-[11px] font-bold uppercase tracking-wider text-white/50 block">
          Select Vehicle to Inspect ({carsWith3D.length} available):
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          {carsWith3D.map((car) => {
            const isSelected = selectedVehicle.id === car.id;
            return (
              <button
                key={car.id}
                type="button"
                onClick={() => setSelectedVehicle(car)}
                className={`flex flex-col text-left p-3 rounded-xl border transition-all ${
                  isSelected
                    ? 'bg-cyan-500/20 border-cyan-400 shadow-cyan-glow'
                    : 'bg-surface-100 border-surface-border hover:bg-surface-50'
                }`}
              >
                <span className="text-[10px] text-cyan-400 font-semibold uppercase truncate">
                  {car.brandName}
                </span>
                <span className="text-xs font-bold text-white truncate">
                  {car.modelName}
                </span>
                <span className="text-[10px] text-white/40 mt-1">
                  {car.bodyStyle}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* The 3D Studio Canvas */}
      <div className="space-y-2">
        <VehicleCanvas vehicle={selectedVehicle} />
      </div>

      {/* Quick Summary of Active Vehicle */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
        <div className="rounded-2xl bg-surface-100 p-5 border border-surface-border space-y-2">
          <span className="text-xs uppercase tracking-wider text-white/40 font-semibold block">
            Powertrain & Architecture
          </span>
          <p className="text-sm font-bold text-white">
            {selectedVehicle.specs.engineConfiguration || selectedVehicle.specs.motorLayout}
          </p>
          <p className="text-xs text-white/60">
            {selectedVehicle.specs.maxPowerHp} horsepower • {selectedVehicle.specs.maxTorqueNm} Nm torque • {selectedVehicle.specs.transmission}
          </p>
        </div>

        <div className="rounded-2xl bg-surface-100 p-5 border border-surface-border space-y-2">
          <span className="text-xs uppercase tracking-wider text-white/40 font-semibold block">
            Speed & Agility
          </span>
          <p className="text-sm font-bold text-cyan-300">
            0-100 km/h in {selectedVehicle.specs.acceleration0to100Kmh}s
          </p>
          <p className="text-xs text-white/60">
            Top speed of {selectedVehicle.specs.topSpeedKmh} km/h • Drive layout: {selectedVehicle.specs.driveType}
          </p>
        </div>

        <div className="rounded-2xl bg-surface-100 p-5 border border-surface-border space-y-2">
          <span className="text-xs uppercase tracking-wider text-white/40 font-semibold block">
            Authentic Data Verification
          </span>
          <p className="text-sm font-bold text-emerald-400 flex items-center gap-1.5">
            <ShieldCheck size={16} />
            <span>Official Factory Verified</span>
          </p>
          <p className="text-xs text-white/60">
            Last verified: {selectedVehicle.verificationDate} by {selectedVehicle.verifiedBy}
          </p>
        </div>
      </div>
    </div>
  );
}

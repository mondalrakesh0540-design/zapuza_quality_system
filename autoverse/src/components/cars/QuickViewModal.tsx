'use client';

import React from 'react';
import Link from 'next/link';
import { Vehicle } from '@/types/vehicle';
import { useStore } from '@/lib/store';
import { convertSpeed, convertPower, convertRange, convertWeight, convertDimension } from '@/lib/units';
import { 
  X, 
  Sparkles, 
  ShieldCheck, 
  Gauge, 
  ArrowRight, 
  Scale, 
  Heart,
  CheckCircle2
} from 'lucide-react';

interface QuickViewModalProps {
  vehicle: Vehicle | null;
  onClose: () => void;
}

export function QuickViewModal({ vehicle, onClose }: QuickViewModalProps) {
  const { 
    unitSystem, 
    isInCompare, 
    toggleCompare, 
    isFavourite, 
    toggleFavourite 
  } = useStore();

  if (!vehicle) return null;

  const inCompare = isInCompare(vehicle.id);
  const favorited = isFavourite(vehicle.id);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="fixed inset-0" onClick={onClose} />

      <div className="relative w-full max-w-3xl rounded-3xl bg-surface-100 border border-surface-border shadow-2xl z-10 overflow-hidden flex flex-col md:flex-row max-h-[90vh]">
        {/* Left Side: Image Preview & Fast Actions */}
        <div className="relative md:w-5/12 bg-surface-200 aspect-[4/3] md:aspect-auto">
          <img
            src={vehicle.heroImage}
            alt={vehicle.modelName}
            className="h-full w-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-surface-100 via-transparent to-transparent md:hidden" />

          {/* 3D availability pill */}
          {vehicle.has3D && (
            <div className="absolute top-4 left-4 flex items-center gap-1.5 rounded-full bg-cyan-500 px-3 py-1 text-xs font-bold text-black shadow-cyan-glow">
              <Sparkles size={13} />
              <span>Interactive 3D Available</span>
            </div>
          )}

          {/* Close button for mobile */}
          <button
            type="button"
            onClick={onClose}
            className="md:hidden absolute top-4 right-4 rounded-full bg-black/60 p-2 text-white"
          >
            <X size={18} />
          </button>
        </div>

        {/* Right Side: Specifications Details */}
        <div className="relative md:w-7/12 p-6 overflow-y-auto space-y-5">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 text-xs text-white/50">
                <span className="font-semibold text-cyan-400">{vehicle.brandName}</span>
                <span>•</span>
                <span>{vehicle.modelYear}</span>
                <span>•</span>
                <span>{vehicle.bodyStyle}</span>
              </div>
              <h3 className="text-2xl font-extrabold text-white font-display mt-0.5">
                {vehicle.modelName}
              </h3>
              <p className="text-xs text-white/60 mt-1">{vehicle.tagline}</p>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="hidden md:flex rounded-lg p-1.5 text-white/50 hover:bg-surface-50 hover:text-white transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Pricing Box */}
          <div className="flex items-center justify-between rounded-xl bg-surface-200/80 p-3.5 border border-surface-border">
            <div>
              <span className="text-[10px] uppercase tracking-wider text-white/50 block">
                Starting {vehicle.priceType} ({vehicle.primaryMarket})
              </span>
              <span className="text-xl font-extrabold text-white font-mono">
                {vehicle.priceFormatted}
              </span>
            </div>
            {vehicle.isVerified && (
              <div className="flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-md border border-emerald-500/20">
                <ShieldCheck size={14} />
                <span>Verified Data</span>
              </div>
            )}
          </div>

          {/* Quick Specs Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="rounded-xl bg-surface-200/50 p-3 border border-surface-border">
              <span className="text-[10px] text-white/40 block">Max Output</span>
              <span className="font-bold text-white font-mono">
                {convertPower(vehicle.specs.maxPowerHp, vehicle.specs.maxPowerKw, unitSystem)}
              </span>
            </div>
            <div className="rounded-xl bg-surface-200/50 p-3 border border-surface-border">
              <span className="text-[10px] text-white/40 block">0 to 100 km/h</span>
              <span className="font-bold text-cyan-300 font-mono">
                {vehicle.specs.acceleration0to100Kmh} seconds
              </span>
            </div>
            <div className="rounded-xl bg-surface-200/50 p-3 border border-surface-border">
              <span className="text-[10px] text-white/40 block">
                {vehicle.fuelType === 'Electric' ? 'Battery & Range' : 'Transmission & Drive'}
              </span>
              <span className="font-bold text-white font-mono">
                {vehicle.fuelType === 'Electric'
                  ? `${vehicle.specs.batteryCapacityKwh} kWh (${convertRange(vehicle.specs.electricRangeKm, unitSystem)})`
                  : `${vehicle.specs.transmission} (${vehicle.specs.driveType})`}
              </span>
            </div>
            <div className="rounded-xl bg-surface-200/50 p-3 border border-surface-border">
              <span className="text-[10px] text-white/40 block">Safety Rating</span>
              <span className="font-bold text-amber-400 font-mono">
                ★ {vehicle.specs.ncapRating || 5} / 5 Stars ({vehicle.specs.ncapAgency})
              </span>
            </div>
          </div>

          {/* Key Strengths */}
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase tracking-wider text-white/50 block font-semibold">
              Top Highlights
            </span>
            <ul className="space-y-1 text-xs text-white/70">
              {vehicle.keyStrengths.slice(0, 2).map((str, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <CheckCircle2 size={13} className="text-cyan-400 shrink-0 mt-0.5" />
                  <span>{str}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Action Row */}
          <div className="flex items-center justify-between border-t border-surface-border pt-4 gap-3">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => toggleCompare(vehicle.id)}
                className={`flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold border transition-all ${
                  inCompare
                    ? 'bg-cyan-500 border-cyan-400 text-black'
                    : 'bg-surface-200 text-white hover:bg-surface-50 border-surface-border'
                }`}
              >
                <Scale size={13} />
                <span>{inCompare ? 'In Compare' : 'Add to Compare'}</span>
              </button>

              <button
                type="button"
                onClick={() => toggleFavourite(vehicle.id)}
                className={`rounded-xl p-2 border transition-all ${
                  favorited
                    ? 'bg-red-500/20 border-red-500 text-red-400'
                    : 'bg-surface-200 text-white/70 hover:text-white border-surface-border'
                }`}
                title="Save favourite"
              >
                <Heart size={14} className={favorited ? 'fill-red-400' : ''} />
              </button>
            </div>

            <Link
              href={`/cars/${vehicle.slug}`}
              onClick={onClose}
              className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-5 py-2 text-xs font-bold text-black shadow-cyan-glow hover:opacity-95 transition-transform"
            >
              <span>Full Details & 3D</span>
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

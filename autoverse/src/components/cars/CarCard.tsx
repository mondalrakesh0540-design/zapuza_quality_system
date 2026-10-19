'use client';

import React from 'react';
import Link from 'next/link';
import { Vehicle } from '@/types/vehicle';
import { useStore } from '@/lib/store';
import { convertSpeed, convertPower, convertRange } from '@/lib/units';
import { 
  Scale, 
  Heart, 
  Sparkles, 
  Eye, 
  ArrowRight, 
  Star,
  Layers,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Compass
} from 'lucide-react';

interface CarCardProps {
  vehicle: Vehicle;
  onQuickView?: (vehicle: Vehicle) => void;
}

export function CarCard({ vehicle, onQuickView }: CarCardProps) {
  const { 
    unitSystem, 
    isInCompare, 
    toggleCompare, 
    isFavourite, 
    toggleFavourite 
  } = useStore();

  const inCompare = isInCompare(vehicle.id);
  const favorited = isFavourite(vehicle.id);

  // Status styling
  const statusConfig = {
    'Currently Available': { label: 'Available in India', bg: 'bg-emerald-500/90 text-black font-bold' },
    'Upcoming': { label: 'Upcoming India Launch', bg: 'bg-amber-400 text-black font-bold' },
    'Imported on Request': { label: 'Imported on Request', bg: 'bg-purple-500/90 text-white font-semibold' },
    'Discontinued': { label: 'Discontinued', bg: 'bg-rose-500/90 text-white font-semibold' },
    'Historical': { label: 'Historical Benchmark', bg: 'bg-blue-500/90 text-white font-semibold' },
  }[vehicle.indiaAvailabilityStatus || 'Currently Available'];

  return (
    <div className="group relative flex flex-col justify-between rounded-2xl bg-surface-100 border border-surface-border hover:border-cyan-500/40 transition-all duration-300 hover:shadow-cyan-glow overflow-hidden">
      {/* Top Media Container */}
      <div className="relative aspect-[16/10] w-full overflow-hidden bg-surface-200">
        <img
          src={vehicle.heroImage}
          alt={`${vehicle.brandName} ${vehicle.modelName}`}
          className="h-full w-full object-cover transition-transform duration-700 ease-out group-hover:scale-105"
          loading="lazy"
        />

        {/* Top Floating Badges */}
        <div className="absolute top-3 left-3 right-3 flex items-center justify-between gap-2 pointer-events-none">
          <div className="flex flex-wrap items-center gap-1.5 pointer-events-auto">
            {/* Availability Status Badge */}
            <span className={`rounded-full px-2.5 py-0.5 text-[10px] backdrop-blur-md shadow-sm ${statusConfig.bg}`}>
              {statusConfig.label}
            </span>

            {/* 3D Model Badge */}
            {vehicle.has3D && (
              <span className="flex items-center gap-1 rounded-full bg-cyan-500/90 px-2.5 py-0.5 text-[10px] font-bold text-black backdrop-blur-md shadow-sm">
                <Sparkles size={10} />
                <span>3D</span>
              </span>
            )}

            {/* Blueprint Badge */}
            {vehicle.blueprint && (
              <span className="flex items-center gap-1 rounded-full bg-blue-600/90 px-2 py-0.5 text-[10px] font-bold text-white backdrop-blur-md shadow-sm">
                <Compass size={10} />
                <span>CAD</span>
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5 pointer-events-auto">
            {/* Favourite Button */}
            <button
              type="button"
              onClick={() => toggleFavourite(vehicle.id)}
              className={`flex h-8 w-8 items-center justify-center rounded-full backdrop-blur-md border transition-all ${
                favorited
                  ? 'bg-red-500/90 border-red-400 text-white shadow-lg'
                  : 'bg-black/60 border-white/10 text-white/70 hover:text-white hover:bg-black/80'
              }`}
              title={favorited ? 'Remove from favourites' : 'Save to favourites'}
            >
              <Heart size={14} className={favorited ? 'fill-white' : ''} />
            </button>

            {/* Compare Button */}
            <button
              type="button"
              onClick={() => toggleCompare(vehicle.id)}
              className={`flex h-8 w-8 items-center justify-center rounded-full backdrop-blur-md border transition-all ${
                inCompare
                  ? 'bg-cyan-500 border-cyan-400 text-black shadow-cyan-glow font-bold'
                  : 'bg-black/60 border-white/10 text-white/70 hover:text-white hover:bg-black/80'
              }`}
              title={inCompare ? 'Remove from compare' : 'Add to compare'}
            >
              <Scale size={14} />
            </button>
          </div>
        </div>

        {/* NCAP Star Badge (Bottom Left of Image) */}
        {vehicle.specs.ncapRating && (
          <div className="absolute bottom-3 left-3 flex items-center gap-1 rounded-md bg-black/80 px-2 py-0.5 text-[10px] font-bold text-amber-300 border border-white/10 backdrop-blur-md">
            <Star size={10} className="fill-amber-300" />
            <span>{vehicle.specs.ncapRating}★ {vehicle.specs.ncapAgency || 'NCAP'}</span>
          </div>
        )}

        {/* Quick View Button on Hover */}
        {onQuickView && (
          <button
            type="button"
            onClick={() => onQuickView(vehicle)}
            className="absolute bottom-3 right-3 flex items-center gap-1.5 rounded-lg bg-black/75 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-md border border-white/20 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black"
          >
            <Eye size={13} />
            <span>Quick Specs</span>
          </button>
        )}
      </div>

      {/* Content Details */}
      <div className="flex flex-1 flex-col justify-between p-5 space-y-4">
        <div>
          {/* Brand & Market */}
          <div className="flex items-center justify-between text-xs text-white/50 mb-1">
            <span className="font-semibold text-cyan-400 tracking-wide uppercase">
              {vehicle.brandName}
            </span>
            <span>{vehicle.modelYear} • {vehicle.bodyStyle}</span>
          </div>

          {/* Model Name */}
          <Link href={`/cars/${vehicle.slug}`}>
            <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition-colors line-clamp-1">
              {vehicle.modelName}
            </h3>
          </Link>

          {/* Tagline */}
          <p className="text-xs text-white/60 line-clamp-2 mt-1 leading-relaxed">
            {vehicle.tagline}
          </p>
        </div>

        {/* Specifications Strip */}
        <div className="grid grid-cols-3 gap-2 rounded-xl bg-surface-200/60 p-2.5 border border-surface-border text-center">
          <div>
            <span className="text-[10px] uppercase tracking-wider text-white/40 block">Power</span>
            <span className="text-xs font-bold text-white font-mono">
              {vehicle.specs.maxPowerHp} hp
            </span>
          </div>
          <div className="border-x border-surface-border">
            <span className="text-[10px] uppercase tracking-wider text-white/40 block">0-100 km/h</span>
            <span className="text-xs font-bold text-cyan-300 font-mono">
              {vehicle.specs.acceleration0to100Kmh}s
            </span>
          </div>
          <div>
            <span className="text-[10px] uppercase tracking-wider text-white/40 block">
              {vehicle.fuelType === 'Electric' ? 'Range' : 'Economy'}
            </span>
            <span className="text-xs font-bold text-white font-mono">
              {vehicle.fuelType === 'Electric'
                ? convertRange(vehicle.specs.electricRangeKm, unitSystem)
                : vehicle.specs.fuelEconomyKmPerL 
                ? `${vehicle.specs.fuelEconomyKmPerL} km/L` 
                : convertSpeed(vehicle.specs.topSpeedKmh, unitSystem)}
            </span>
          </div>
        </div>

        {/* Price & CTA Action */}
        <div className="flex items-center justify-between border-t border-surface-border pt-4">
          <div>
            <span className="text-[10px] uppercase tracking-wider text-white/40 block">
              Starting {vehicle.priceType}
            </span>
            <span className="text-base font-extrabold text-white font-mono">
              {vehicle.priceFormatted}
            </span>
          </div>

          <Link
            href={`/cars/${vehicle.slug}`}
            className="flex items-center gap-1.5 rounded-xl bg-surface-50 px-3.5 py-2 text-xs font-semibold text-white border border-surface-border group-hover:border-cyan-500/50 group-hover:bg-cyan-500 group-hover:text-black transition-all"
          >
            <span>Explore</span>
            <ArrowRight size={13} />
          </Link>
        </div>
      </div>
    </div>
  );
}

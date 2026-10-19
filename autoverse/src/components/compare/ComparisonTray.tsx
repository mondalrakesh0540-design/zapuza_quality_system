'use client';

import React from 'react';
import Link from 'next/link';
import { useStore } from '@/lib/store';
import { VEHICLES } from '@/data/vehicles';
import { Scale, X, ArrowRight, Trash2 } from 'lucide-react';

export function ComparisonTray() {
  const { comparisonIds, removeFromCompare, clearCompare } = useStore();

  if (comparisonIds.length === 0) return null;

  const selectedCars = comparisonIds
    .map(id => VEHICLES.find(v => v.id === id))
    .filter(Boolean);

  return (
    <div className="fixed bottom-4 left-4 right-4 z-40 mx-auto max-w-4xl animate-slideUp">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 rounded-2xl bg-surface-100/95 p-4 border border-cyan-500/40 backdrop-blur-xl shadow-cyan-glow">
        {/* Left: Summary */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500 text-black">
            <Scale size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
                Comparison Tray
              </span>
              <span className="text-xs text-white/50">
                ({selectedCars.length} / 4 vehicles)
              </span>
            </div>
            <p className="text-xs text-white/70">
              Side-by-side specifications, performance & dimensions
            </p>
          </div>
        </div>

        {/* Center: Selected Car Thumbnails */}
        <div className="flex items-center gap-2 overflow-x-auto max-w-full py-1">
          {selectedCars.map((car) => {
            if (!car) return null;
            return (
              <div
                key={car.id}
                className="group relative flex items-center gap-2 rounded-lg bg-surface-50 px-2.5 py-1.5 border border-surface-border"
              >
                <img
                  src={car.heroImage}
                  alt={car.modelName}
                  className="h-7 w-11 object-cover rounded"
                />
                <div className="text-left">
                  <p className="text-[11px] font-semibold text-white leading-tight truncate max-w-[90px]">
                    {car.modelName}
                  </p>
                  <p className="text-[9px] text-white/50">{car.brandName}</p>
                </div>
                <button
                  type="button"
                  onClick={() => removeFromCompare(car.id)}
                  className="ml-1 text-white/40 hover:text-red-400 transition-colors"
                  title="Remove vehicle"
                >
                  <X size={13} />
                </button>
              </div>
            );
          })}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={clearCompare}
            className="flex items-center gap-1 rounded-xl px-2.5 py-2 text-xs text-white/50 hover:text-white transition-colors"
            title="Clear comparison tray"
          >
            <Trash2 size={14} />
            <span className="hidden sm:inline">Clear</span>
          </button>

          <Link
            href="/compare"
            className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-4 py-2 text-xs font-bold text-black shadow-cyan-glow hover:opacity-95 transition-all"
          >
            <span>Compare Now</span>
            <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    </div>
  );
}

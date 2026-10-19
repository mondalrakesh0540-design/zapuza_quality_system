'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { VEHICLES } from '@/data/vehicles';
import { BRANDS } from '@/data/brands';
import { formatPrice } from '@/lib/units';
import { Search, X, Car, ArrowRight, Zap, Shield, Sparkles } from 'lucide-react';

export function SearchModal() {
  const { isSearchOpen, setIsSearchOpen } = useStore();
  const [query, setQuery] = useState('');
  const router = useRouter();

  // Listen for Cmd+K or Ctrl+K shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen(!isSearchOpen);
      }
      if (e.key === 'Escape') {
        setIsSearchOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSearchOpen, setIsSearchOpen]);

  if (!isSearchOpen) return null;

  const cleanQuery = query.toLowerCase().trim();

  const matchingVehicles = cleanQuery
    ? VEHICLES.filter((v) => {
        return (
          v.modelName.toLowerCase().includes(cleanQuery) ||
          v.brandName.toLowerCase().includes(cleanQuery) ||
          v.bodyStyle.toLowerCase().includes(cleanQuery) ||
          v.fuelType.toLowerCase().includes(cleanQuery) ||
          v.tagline.toLowerCase().includes(cleanQuery)
        );
      })
    : VEHICLES.slice(0, 4); // Suggest top 4 when empty

  const matchingBrands = cleanQuery
    ? BRANDS.filter((b) => {
        return (
          b.name.toLowerCase().includes(cleanQuery) ||
          b.country.toLowerCase().includes(cleanQuery)
        );
      })
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      {/* Background click to close */}
      <div
        className="fixed inset-0"
        onClick={() => setIsSearchOpen(false)}
      />

      <div className="relative w-full max-w-2xl rounded-2xl bg-surface-100 p-6 border border-surface-border shadow-2xl z-10 space-y-4">
        {/* Search Input Bar */}
        <div className="relative flex items-center border-b border-surface-border pb-4">
          <Search className="h-5 w-5 text-cyan-400 mr-3 shrink-0" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by brand, model, body style (e.g. 'Porsche', 'SUV', 'Electric')..."
            className="w-full bg-transparent text-base text-white placeholder-white/40 focus:outline-none"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="p-1 text-white/50 hover:text-white"
            >
              <X size={16} />
            </button>
          )}
          <button
            type="button"
            onClick={() => setIsSearchOpen(false)}
            className="ml-2 rounded-lg bg-surface-200 px-2 py-1 text-xs text-white/60 hover:text-white border border-surface-border"
          >
            ESC
          </button>
        </div>

        {/* Results Body */}
        <div className="max-h-[60vh] overflow-y-auto space-y-4 pr-1">
          {/* Matching Brands */}
          {matchingBrands.length > 0 && (
            <div className="space-y-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-white/40">
                Automotive Brands
              </span>
              <div className="grid grid-cols-2 gap-2">
                {matchingBrands.map((b) => (
                  <Link
                    key={b.id}
                    href={`/brands/${b.slug}`}
                    onClick={() => setIsSearchOpen(false)}
                    className="flex items-center gap-2.5 rounded-xl bg-surface-200/80 p-2.5 border border-surface-border hover:border-cyan-500/40 transition-colors"
                  >
                    <span className="text-xl">{b.flagEmoji}</span>
                    <div>
                      <p className="text-xs font-bold text-white">{b.name}</p>
                      <p className="text-[10px] text-white/50">{b.country} • {b.modelCount} models</p>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Vehicles Section */}
          <div className="space-y-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-white/40">
              {cleanQuery ? `Vehicles Matching "${query}"` : 'Recommended Vehicles'}
            </span>

            {matchingVehicles.length === 0 ? (
              <div className="py-8 text-center text-white/50 text-sm">
                No vehicles matched your search. Try searching for "Tata", "Porsche", "EV", or "SUV".
              </div>
            ) : (
              <div className="space-y-2">
                {matchingVehicles.map((car) => (
                  <Link
                    key={car.id}
                    href={`/cars/${car.slug}`}
                    onClick={() => setIsSearchOpen(false)}
                    className="group flex items-center justify-between rounded-xl bg-surface-200/60 p-3 border border-surface-border hover:border-cyan-500/40 hover:bg-surface-50 transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <img
                        src={car.heroImage}
                        alt={car.modelName}
                        className="h-12 w-18 object-cover rounded-lg border border-surface-border"
                      />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-cyan-400">
                            {car.brandName}
                          </span>
                          <span className="text-xs text-white/40">•</span>
                          <span className="text-xs text-white/60">
                            {car.modelYear}
                          </span>
                          {car.has3D && (
                            <span className="flex items-center gap-0.5 rounded bg-cyan-500/20 px-1.5 py-0.2 text-[9px] font-bold text-cyan-300">
                              <Sparkles size={10} /> 3D
                            </span>
                          )}
                        </div>
                        <h4 className="text-sm font-bold text-white group-hover:text-cyan-300 transition-colors">
                          {car.modelName}
                        </h4>
                        <div className="flex items-center gap-3 text-[11px] text-white/50">
                          <span>{car.bodyStyle}</span>
                          <span>•</span>
                          <span>{car.fuelType}</span>
                          <span>•</span>
                          <span className="text-white/80 font-mono font-medium">
                            {car.priceFormatted}
                          </span>
                        </div>
                      </div>
                    </div>

                    <ArrowRight
                      size={16}
                      className="text-white/40 group-hover:text-cyan-400 group-hover:translate-x-1 transition-all"
                    />
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer shortcuts */}
        <div className="flex items-center justify-between border-t border-surface-border pt-3 text-xs text-white/40">
          <Link
            href="/cars"
            onClick={() => setIsSearchOpen(false)}
            className="text-cyan-400 hover:underline flex items-center gap-1 font-medium"
          >
            <span>Browse Full Catalog with Advanced Filters</span>
            <ArrowRight size={12} />
          </Link>
          <span>Press ESC to exit</span>
        </div>
      </div>
    </div>
  );
}

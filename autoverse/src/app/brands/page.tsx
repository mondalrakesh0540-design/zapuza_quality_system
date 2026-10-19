'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { BRANDS } from '@/data/brands';
import { VEHICLES } from '@/data/vehicles';
import { Search, Globe, ExternalLink, ArrowRight, Car } from 'lucide-react';

export default function BrandsPage() {
  const [search, setSearch] = useState('');
  const [selectedCountry, setSelectedCountry] = useState<string>('All');

  const countries = ['All', ...Array.from(new Set(BRANDS.map(b => b.country)))];

  const filteredBrands = BRANDS.filter((brand) => {
    const matchesSearch = 
      brand.name.toLowerCase().includes(search.toLowerCase()) ||
      brand.country.toLowerCase().includes(search.toLowerCase()) ||
      brand.description.toLowerCase().includes(search.toLowerCase());

    const matchesCountry = selectedCountry === 'All' || brand.country === selectedCountry;

    return matchesSearch && matchesCountry;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-surface-border pb-6">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
            Global Automotive Directory
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white font-display mt-1">
            Automotive Brands
          </h1>
          <p className="text-sm text-white/60 mt-1">
            Explore world-renowned manufacturers from India, Germany, USA, Italy, the UK, Japan, and Croatia.
          </p>
        </div>

        {/* Search & Country Filter */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-cyan-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search brands..."
              className="rounded-xl bg-surface-100 pl-9 pr-3 py-2 text-xs text-white border border-surface-border focus:border-cyan-500 focus:outline-none w-52"
            />
          </div>

          <select
            value={selectedCountry}
            onChange={(e) => setSelectedCountry(e.target.value)}
            className="rounded-xl bg-surface-100 px-3 py-2 text-xs font-medium text-white border border-surface-border focus:border-cyan-500 focus:outline-none cursor-pointer"
          >
            {countries.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Brands Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredBrands.map((brand) => {
          const brandVehicles = VEHICLES.filter(v => v.brandId === brand.id);
          return (
            <div
              key={brand.id}
              className="group relative flex flex-col justify-between rounded-2xl bg-surface-100 border border-surface-border hover:border-cyan-500/40 p-6 space-y-5 transition-all hover:shadow-cyan-glow"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{brand.flagEmoji}</span>
                      <span className="text-xs text-white/50">{brand.country}</span>
                      <span className="text-white/30">•</span>
                      <span className="text-xs text-white/40 font-mono">Est. {brand.foundedYear}</span>
                    </div>
                    <Link href={`/brands/${brand.slug}`}>
                      <h3 className="text-xl font-bold text-white group-hover:text-cyan-300 transition-colors mt-2">
                        {brand.name}
                      </h3>
                    </Link>
                  </div>

                  <span className="rounded-md bg-surface-200 px-2.5 py-1 text-xs font-bold text-cyan-400 font-mono">
                    {brand.modelCount} models
                  </span>
                </div>

                <p className="text-xs text-white/70 line-clamp-3 mt-3 leading-relaxed">
                  {brand.description}
                </p>

                {/* Popular Models List */}
                <div className="pt-3 border-t border-surface-border mt-4">
                  <span className="text-[10px] uppercase tracking-wider text-white/40 font-semibold block mb-1">
                    Popular Models:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {brand.popularModels.map((m, i) => (
                      <span
                        key={i}
                        className="rounded bg-surface-200 px-2 py-0.5 text-[11px] text-white/80"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2 border-t border-surface-border">
                <a
                  href={brand.website}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 text-[11px] text-white/50 hover:text-white"
                >
                  <span>Official Website</span>
                  <ExternalLink size={11} />
                </a>

                <Link
                  href={`/brands/${brand.slug}`}
                  className="flex items-center gap-1.5 rounded-xl bg-surface-50 px-3.5 py-1.5 text-xs font-semibold text-cyan-400 hover:text-white border border-surface-border group-hover:border-cyan-500/40"
                >
                  <span>View Lineup</span>
                  <ArrowRight size={13} />
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

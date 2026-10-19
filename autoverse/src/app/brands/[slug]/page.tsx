'use client';

import React, { useState } from 'react';
import { notFound, useParams } from 'next/navigation';
import Link from 'next/link';
import { BRANDS } from '@/data/brands';
import { VEHICLES } from '@/data/vehicles';
import { Vehicle } from '@/types/vehicle';
import { CarCard } from '@/components/cars/CarCard';
import { QuickViewModal } from '@/components/cars/QuickViewModal';
import { 
  ArrowLeft, 
  ExternalLink, 
  Globe, 
  Building, 
  Calendar, 
  ShieldCheck, 
  Car 
} from 'lucide-react';

export default function BrandDetailPage() {
  const params = useParams();
  const slug = params?.slug as string;

  const brand = BRANDS.find(b => b.slug === slug || b.id === slug);
  const [quickViewVehicle, setQuickViewVehicle] = useState<Vehicle | null>(null);

  if (!brand) {
    return notFound();
  }

  const brandVehicles = VEHICLES.filter(v => v.brandId === brand.id);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      {/* Back button */}
      <div>
        <Link
          href="/brands"
          className="inline-flex items-center gap-1.5 text-xs text-white/50 hover:text-cyan-400 transition-colors"
        >
          <ArrowLeft size={14} />
          <span>Back to Brands Directory</span>
        </Link>
      </div>

      {/* Brand Hero Banner Card */}
      <div className="relative rounded-3xl overflow-hidden border border-surface-border bg-surface-100 p-8 lg:p-12 shadow-2xl">
        <img
          src={brand.heroBanner}
          alt={brand.name}
          className="absolute inset-0 h-full w-full object-cover opacity-20 pointer-events-none"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-background via-background/90 to-transparent" />

        <div className="relative z-10 max-w-3xl space-y-5">
          <div className="flex flex-wrap items-center gap-3 text-xs text-white/60">
            <span className="text-3xl">{brand.flagEmoji}</span>
            <span className="font-semibold text-white">{brand.country}</span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Calendar size={13} className="text-cyan-400" />
              <span>Founded {brand.foundedYear}</span>
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Building size={13} className="text-cyan-400" />
              <span>{brand.headquarters}</span>
            </span>
          </div>

          <h1 className="text-4xl sm:text-5xl font-extrabold text-white font-display">
            {brand.name}
          </h1>

          <p className="text-sm sm:text-base text-white/75 leading-relaxed">
            {brand.description}
          </p>

          <div className="flex items-center gap-4 pt-2">
            <a
              href={brand.website}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500 px-4 py-2 text-xs font-bold text-black hover:bg-cyan-400 transition-colors"
            >
              <span>Visit Official Website</span>
              <ExternalLink size={13} />
            </a>

            <span className="text-xs text-white/50">
              {brandVehicles.length} detailed models cataloged
            </span>
          </div>
        </div>
      </div>

      {/* Models Lineup Section */}
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-surface-border pb-4">
          <div>
            <h2 className="text-2xl font-bold text-white font-display">
              {brand.name} Model Lineup
            </h2>
            <p className="text-xs text-white/50 mt-1">
              Click any car to explore full technical specifications and interactive 3D model.
            </p>
          </div>
        </div>

        {brandVehicles.length === 0 ? (
          <div className="rounded-2xl bg-surface-100 p-12 text-center border border-surface-border space-y-3">
            <Car size={32} className="mx-auto text-white/30" />
            <h3 className="text-lg font-bold text-white">No Models Cataloged Yet</h3>
            <p className="text-xs text-white/60 max-w-sm mx-auto">
              We are currently verifying the factory specifications for upcoming {brand.name} models.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {brandVehicles.map((car) => (
              <CarCard
                key={car.id}
                vehicle={car}
                onQuickView={(v) => setQuickViewVehicle(v)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Quick View Modal */}
      <QuickViewModal
        vehicle={quickViewVehicle}
        onClose={() => setQuickViewVehicle(null)}
      />
    </div>
  );
}

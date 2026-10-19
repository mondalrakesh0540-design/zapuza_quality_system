'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { VEHICLES, getFeaturedVehicles, getTrendingVehicles } from '@/data/vehicles';
import { BRANDS } from '@/data/brands';
import { Vehicle } from '@/types/vehicle';
import { CarCard } from '@/components/cars/CarCard';
import { QuickViewModal } from '@/components/cars/QuickViewModal';
import { VehicleCanvas } from '@/components/3d/VehicleCanvas';
import { 
  Sparkles, 
  ArrowRight, 
  Search, 
  Scale, 
  ChevronDown, 
  ShieldCheck, 
  Zap, 
  Compass, 
  Layers, 
  Flame,
  Award,
  BookOpen
} from 'lucide-react';

export default function HomePage() {
  const router = useRouter();
  const [quickViewVehicle, setQuickViewVehicle] = useState<Vehicle | null>(null);
  const [heroSearch, setHeroSearch] = useState('');
  
  // Choose flagship 3D hero car (Porsche 911 GT3 RS or Rimac Nevera)
  const heroCar = VEHICLES.find(v => v.id === 'porsche-911-gt3-rs') || VEHICLES[0];
  const featuredCars = getFeaturedVehicles();
  const trendingCars = getTrendingVehicles();

  const handleHeroSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (heroSearch.trim()) {
      router.push(`/cars?search=${encodeURIComponent(heroSearch.trim())}`);
    } else {
      router.push('/cars');
    }
  };

  const categories = [
    { name: 'Electric (EV)', slug: 'Electric', icon: Zap, count: '3 models', image: 'https://images.unsplash.com/photo-1560958089-b8a1929cea89?auto=format&fit=crop&w=600&q=80' },
    { name: 'SUVs & 4x4', slug: 'SUV', icon: Compass, count: '2 models', image: 'https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?auto=format&fit=crop&w=600&q=80' },
    { name: 'Sports Cars', slug: 'Sports Car', icon: Flame, count: '2 models', image: 'https://images.unsplash.com/photo-1614162692292-7ac56d7f7f1e?auto=format&fit=crop&w=600&q=80' },
    { name: 'Hypercars', slug: 'Hypercar', icon: Sparkles, count: '2 models', image: 'https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=600&q=80' },
    { name: 'Luxury Sedans', slug: 'Sedan', icon: Layers, count: '1 model', image: 'https://images.unsplash.com/photo-1555353540-64580b51c258?auto=format&fit=crop&w=600&q=80' },
    { name: 'Off-Road Pure', slug: 'Off-Road', icon: Award, count: '1 model', image: 'https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=600&q=80' },
  ];

  return (
    <div className="w-full space-y-24 pb-20">
      {/* ========================================================= */}
      {/* SECTION A: HERO SECTION WITH LIVE 3D INTERACTIVE VIEWER */}
      {/* ========================================================= */}
      <section className="relative min-h-[92vh] flex flex-col justify-between pt-10 pb-6 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        {/* Background Ambience */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-cyan-500/10 blur-[140px] pointer-events-none rounded-full" />

        <div className="space-y-6 text-center max-w-4xl mx-auto relative z-10">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 rounded-full bg-surface-100/90 px-4 py-1.5 border border-cyan-500/30 backdrop-blur-md shadow-cyan-glow">
            <span className="flex h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-300">
              Interactive 3D Automotive Experience
            </span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white font-display leading-[1.08]">
            DISCOVER THE WORLD OF <br className="hidden sm:inline" />
            <span className="text-gradient-cyan">AUTOMOTIVE EXCELLENCE.</span>
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg text-white/70 max-w-2xl mx-auto leading-relaxed">
            Explore every detail. Compare every specification. Experience cars in real-time interactive 3D with authentic manufacturer data.
          </p>

          {/* CTAs and Search Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <Link
              href="/cars"
              className="w-full sm:w-auto flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-600 px-7 py-3.5 text-sm font-bold text-black shadow-cyan-glow hover:opacity-95 transition-all"
            >
              <span>Explore Cars</span>
              <ArrowRight size={16} />
            </Link>

            <Link
              href="/compare"
              className="w-full sm:w-auto flex items-center justify-center gap-2 rounded-xl bg-surface-100/90 px-7 py-3.5 text-sm font-semibold text-white border border-surface-border hover:border-cyan-500/40 hover:bg-surface-50 transition-all"
            >
              <Scale size={16} className="text-cyan-400" />
              <span>Compare Vehicles</span>
            </Link>
          </div>

          {/* Hero Quick Search Box */}
          <form
            onSubmit={handleHeroSearch}
            className="relative max-w-xl mx-auto mt-4 flex items-center rounded-2xl bg-surface-100/95 p-1.5 border border-surface-border shadow-2xl backdrop-blur-md focus-within:border-cyan-500/60 transition-all"
          >
            <Search className="h-5 w-5 text-cyan-400 ml-3 mr-2 shrink-0" />
            <input
              type="text"
              value={heroSearch}
              onChange={(e) => setHeroSearch(e.target.value)}
              placeholder="Search by brand, model, body style or fuel type (e.g. 'Nexon', 'Porsche', 'EV')..."
              className="w-full bg-transparent text-sm text-white placeholder-white/40 focus:outline-none py-2"
            />
            <button
              type="submit"
              className="rounded-xl bg-cyan-500 px-5 py-2 text-xs font-bold text-black hover:bg-cyan-400 transition-colors"
            >
              Search
            </button>
          </form>
        </div>

        {/* 3D Hero Car Canvas Showcase */}
        <div className="mt-8 relative z-10">
          <VehicleCanvas vehicle={heroCar} />
        </div>

        {/* Scroll Indicator */}
        <div className="flex flex-col items-center justify-center pt-6 text-white/40 text-xs">
          <span>Scroll to explore vehicle lineup</span>
          <ChevronDown size={18} className="animate-bounce mt-1 text-cyan-400" />
        </div>
      </section>

      {/* ========================================================= */}
      {/* SECTION B: FEATURED CARS WITH QUICK-VIEW & 3D CONTROLS */}
      {/* ========================================================= */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-surface-border pb-5">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
              <Sparkles size={14} />
              <span>Handpicked Vehicles</span>
            </div>
            <h2 className="text-3xl font-extrabold text-white font-display mt-1">
              Featured Flagship Models
            </h2>
            <p className="text-sm text-white/60 mt-1">
              Groundbreaking engineering from India, Germany, USA, Italy, and Croatia.
            </p>
          </div>

          <Link
            href="/cars"
            className="flex items-center gap-1.5 text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            <span>View All {VEHICLES.length} Vehicles</span>
            <ArrowRight size={14} />
          </Link>
        </div>

        {/* Vehicle Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {featuredCars.map((car) => (
            <CarCard
              key={car.id}
              vehicle={car}
              onQuickView={(v) => setQuickViewVehicle(v)}
            />
          ))}
        </div>
      </section>

      {/* ========================================================= */}
      {/* SECTION C: BROWSE BY CATEGORY */}
      {/* ========================================================= */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
            Form Factors & Powertrains
          </span>
          <h2 className="text-3xl font-extrabold text-white font-display mt-1">
            Browse by Body & Category
          </h2>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {categories.map((cat) => (
            <Link
              key={cat.name}
              href={`/cars?body=${encodeURIComponent(cat.slug)}`}
              className="group relative flex flex-col justify-between h-44 rounded-2xl overflow-hidden border border-surface-border bg-surface-100 p-4 transition-all duration-300 hover:border-cyan-500/50 hover:shadow-cyan-glow"
            >
              <img
                src={cat.image}
                alt={cat.name}
                className="absolute inset-0 h-full w-full object-cover opacity-40 transition-transform duration-500 group-hover:scale-110"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black via-black/60 to-transparent" />

              <div className="relative z-10 flex items-center justify-between">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-100/90 text-cyan-400 border border-white/10 backdrop-blur-md">
                  <cat.icon size={16} />
                </div>
                <span className="text-[10px] text-white/50">{cat.count}</span>
              </div>

              <div className="relative z-10">
                <h4 className="text-sm font-bold text-white group-hover:text-cyan-300 transition-colors">
                  {cat.name}
                </h4>
                <div className="flex items-center gap-1 text-[11px] text-cyan-400 font-medium mt-1">
                  <span>Explore</span>
                  <ArrowRight size={11} className="group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ========================================================= */}
      {/* SECTION D: BROWSE BY BRAND DIRECTORY */}
      {/* ========================================================= */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-surface-border pb-5">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
              Global & Indian Manufacturers
            </span>
            <h2 className="text-3xl font-extrabold text-white font-display mt-1">
              Browse by Automotive Brand
            </h2>
          </div>
          <Link
            href="/brands"
            className="flex items-center gap-1 text-xs font-semibold text-cyan-400 hover:text-cyan-300"
          >
            <span>View All {BRANDS.length} Brands</span>
            <ArrowRight size={14} />
          </Link>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {BRANDS.map((brand) => (
            <Link
              key={brand.id}
              href={`/brands/${brand.slug}`}
              className="group flex flex-col justify-between rounded-2xl bg-surface-100 p-4 border border-surface-border hover:border-cyan-500/40 hover:bg-surface-50 transition-all text-left"
            >
              <div className="flex items-center justify-between">
                <span className="text-2xl">{brand.flagEmoji}</span>
                <span className="text-[10px] font-mono text-white/40">
                  {brand.foundedYear}
                </span>
              </div>

              <div className="mt-4">
                <h4 className="text-sm font-bold text-white group-hover:text-cyan-300 transition-colors">
                  {brand.name}
                </h4>
                <p className="text-[11px] text-white/50">{brand.country}</p>
                <span className="mt-2 inline-block rounded-md bg-surface-200 px-2 py-0.5 text-[10px] text-cyan-400 font-medium">
                  {brand.modelCount} models
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ========================================================= */}
      {/* SECTION E: TRENDING & RECENTLY VERIFIED LAUNCHES */}
      {/* ========================================================= */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="flex items-center justify-between border-b border-surface-border pb-5">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-400">
              <Flame size={14} />
              <span>Trending Now</span>
            </div>
            <h2 className="text-3xl font-extrabold text-white font-display mt-1">
              New Launches & High Demand
            </h2>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {trendingCars.slice(0, 3).map((car) => (
            <CarCard
              key={car.id}
              vehicle={car}
              onQuickView={(v) => setQuickViewVehicle(v)}
            />
          ))}
        </div>
      </section>

      {/* ========================================================= */}
      {/* SECTION F: AUTOMOTIVE INSIGHTS & EXPLAINERS */}
      {/* ========================================================= */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
            Technical Engineering & Analysis
          </span>
          <h2 className="text-3xl font-extrabold text-white font-display mt-1">
            Automotive Insights
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="rounded-2xl bg-surface-100 p-6 border border-surface-border space-y-4 hover:border-cyan-500/40 transition-colors">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/20 text-cyan-400">
              <Zap size={20} />
            </div>
            <h3 className="text-lg font-bold text-white">
              Electric vs Petrol: The Real Cost of Ownership in 2026
            </h3>
            <p className="text-xs text-white/60 leading-relaxed">
              Analyzing battery degradation over 150,000 km, highway charging costs vs petrol pump prices, and maintenance differences between ICE transmissions and direct-drive EV inverters.
            </p>
            <Link
              href="/insights"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-400 hover:text-cyan-300"
            >
              <span>Read Full Analysis</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          <div className="rounded-2xl bg-surface-100 p-6 border border-surface-border space-y-4 hover:border-cyan-500/40 transition-colors">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/20 text-blue-400">
              <Compass size={20} />
            </div>
            <h3 className="text-lg font-bold text-white">
              Active Aerodynamics: How 911 GT3 RS Generates 860 kg Downforce
            </h3>
            <p className="text-xs text-white/60 leading-relaxed">
              Deep dive into hydraulic DRS flap mechanisms, central radiators replacing luggage compartments, and venturi underbody diffusers creating massive high-speed ground effect.
            </p>
            <Link
              href="/insights"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-400 hover:text-cyan-300"
            >
              <span>Explore Aero Mechanics</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          <div className="rounded-2xl bg-surface-100 p-6 border border-surface-border space-y-4 hover:border-cyan-500/40 transition-colors">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400">
              <ShieldCheck size={20} />
            </div>
            <h3 className="text-lg font-bold text-white">
              Bharat NCAP vs Euro NCAP: Crash Protocols Decoded
            </h3>
            <p className="text-xs text-white/60 leading-relaxed">
              Comparing frontal offset, side pole impact velocities, pedestrian protection mandates, and electronic stability control test criteria between Indian and European testing authorities.
            </p>
            <Link
              href="/insights"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-400 hover:text-cyan-300"
            >
              <span>Read Safety Guide</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </section>

      {/* Quick View Modal */}
      <QuickViewModal
        vehicle={quickViewVehicle}
        onClose={() => setQuickViewVehicle(null)}
      />
    </div>
  );
}

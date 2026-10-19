'use client';

import React, { useState, useMemo, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { VEHICLES } from '@/data/vehicles';
import { BRANDS } from '@/data/brands';
import { Vehicle, BodyStyle, FuelType, IndiaAvailabilityStatus, TransmissionType } from '@/types/vehicle';
import { INDIAN_CITIES } from '@/lib/pricing';
import { CarCard } from '@/components/cars/CarCard';
import { QuickViewModal } from '@/components/cars/QuickViewModal';
import { 
  Search, 
  SlidersHorizontal, 
  X, 
  RotateCcw, 
  Sparkles, 
  Check, 
  Car, 
  ChevronDown,
  MapPin,
  Compass,
  Zap,
  Gauge,
  Sliders,
  Layers,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Filter
} from 'lucide-react';

function CarsContent() {
  const searchParams = useSearchParams();
  const initialSearch = searchParams.get('search') || '';
  const initialBody = searchParams.get('body') || '';
  const initialBrand = searchParams.get('brand') || '';
  const initialFuel = searchParams.get('fuel') || '';
  const initialStatus = searchParams.get('status') || '';

  // Filter States
  const [searchQuery, setSearchQuery] = useState(initialSearch);
  const [selectedBrands, setSelectedBrands] = useState<string[]>(initialBrand ? [initialBrand] : []);
  const [selectedBodies, setSelectedBodies] = useState<string[]>(initialBody ? [initialBody] : []);
  const [selectedFuels, setSelectedFuels] = useState<string[]>(initialFuel ? [initialFuel] : []);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>(initialStatus ? [initialStatus] : []);
  const [selectedTransmissions, setSelectedTransmissions] = useState<string[]>([]);
  const [selectedSeatings, setSelectedSeatings] = useState<number[]>([]);
  const [selectedCity, setSelectedCity] = useState<string>('delhi');
  const [priceBracket, setPriceBracket] = useState<string>('all');
  const [minPower, setMinPower] = useState<number>(0);
  const [minEvRange, setMinEvRange] = useState<number>(0);
  const [has3DOnly, setHas3DOnly] = useState(false);
  const [hasBlueprintOnly, setHasBlueprintOnly] = useState(false);
  const [sortBy, setSortBy] = useState<string>('popular');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 9;

  const [mobileFilterOpen, setMobileFilterOpen] = useState(false);
  const [quickViewVehicle, setQuickViewVehicle] = useState<Vehicle | null>(null);

  // Available Filter Options
  const allBodyStyles: BodyStyle[] = [
    'SUV', 'Compact SUV', 'Sedan', 'Hatchback', 'MUV', 'Sports Car', 'Coupe', 'Off-Road', 'Luxury', 'Hypercar'
  ];

  const allFuelTypes: FuelType[] = [
    'Electric', 'Petrol', 'Diesel', 'Hybrid', 'Plug-in Hybrid'
  ];

  const allStatuses: IndiaAvailabilityStatus[] = [
    'Currently Available', 'Upcoming', 'Imported on Request', 'Discontinued'
  ];

  const allTransmissions = [
    'Manual', 'Automatic', 'Dual-Clutch (DCT)', 'e-CVT', 'Single-Speed (EV)'
  ];

  const seatingOptions = [2, 4, 5, 7, 8];

  const priceBrackets = [
    { id: 'all', label: 'All Price Ranges' },
    { id: 'under-15l', label: 'Under ₹15 Lakh' },
    { id: '15l-30l', label: '₹15 Lakh - ₹30 Lakh' },
    { id: '30l-75l', label: '₹30 Lakh - ₹75 Lakh' },
    { id: '75l-2cr', label: '₹75 Lakh - ₹2 Crore' },
    { id: 'above-2cr', label: 'Above ₹2 Crore' },
  ];

  // Toggle Handlers
  const toggleBrand = (brandId: string) => {
    setSelectedBrands(prev => 
      prev.includes(brandId) ? prev.filter(b => b !== brandId) : [...prev, brandId]
    );
    setCurrentPage(1);
  };

  const toggleBody = (body: string) => {
    setSelectedBodies(prev => 
      prev.includes(body) ? prev.filter(b => b !== body) : [...prev, body]
    );
    setCurrentPage(1);
  };

  const toggleFuel = (fuel: string) => {
    setSelectedFuels(prev => 
      prev.includes(fuel) ? prev.filter(f => f !== fuel) : [...prev, fuel]
    );
    setCurrentPage(1);
  };

  const toggleStatus = (status: string) => {
    setSelectedStatuses(prev => 
      prev.includes(status) ? prev.filter(s => s !== status) : [...prev, status]
    );
    setCurrentPage(1);
  };

  const toggleTransmission = (t: string) => {
    setSelectedTransmissions(prev => 
      prev.includes(t) ? prev.filter(item => item !== t) : [...prev, t]
    );
    setCurrentPage(1);
  };

  const toggleSeating = (seats: number) => {
    setSelectedSeatings(prev => 
      prev.includes(seats) ? prev.filter(s => s !== seats) : [...prev, seats]
    );
    setCurrentPage(1);
  };

  const clearAllFilters = () => {
    setSearchQuery('');
    setSelectedBrands([]);
    setSelectedBodies([]);
    setSelectedFuels([]);
    setSelectedStatuses([]);
    setSelectedTransmissions([]);
    setSelectedSeatings([]);
    setPriceBracket('all');
    setMinPower(0);
    setMinEvRange(0);
    setHas3DOnly(false);
    setHasBlueprintOnly(false);
    setSortBy('popular');
    setCurrentPage(1);
  };

  const hasActiveFilters = 
    searchQuery.trim() !== '' ||
    selectedBrands.length > 0 ||
    selectedBodies.length > 0 ||
    selectedFuels.length > 0 ||
    selectedStatuses.length > 0 ||
    selectedTransmissions.length > 0 ||
    selectedSeatings.length > 0 ||
    priceBracket !== 'all' ||
    minPower > 0 ||
    minEvRange > 0 ||
    has3DOnly ||
    hasBlueprintOnly;

  // Filter & Sort Logic
  const filteredVehicles = useMemo(() => {
    let list = [...VEHICLES];

    // 1. Text Search (Model, Brand, Tagline)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(v => 
        v.modelName.toLowerCase().includes(q) ||
        v.brandName.toLowerCase().includes(q) ||
        v.bodyStyle.toLowerCase().includes(q) ||
        v.fuelType.toLowerCase().includes(q) ||
        v.tagline.toLowerCase().includes(q)
      );
    }

    // 2. Brand Filter
    if (selectedBrands.length > 0) {
      list = list.filter(v => selectedBrands.includes(v.brandId));
    }

    // 3. Body Style Filter
    if (selectedBodies.length > 0) {
      list = list.filter(v => selectedBodies.includes(v.bodyStyle));
    }

    // 4. Fuel Types
    if (selectedFuels.length > 0) {
      list = list.filter(v => selectedFuels.includes(v.fuelType));
    }

    // 5. India Availability Status
    if (selectedStatuses.length > 0) {
      list = list.filter(v => selectedStatuses.includes(v.indiaAvailabilityStatus));
    }

    // 6. Transmissions
    if (selectedTransmissions.length > 0) {
      list = list.filter(v => {
        const transStr = v.specs.transmission.toLowerCase();
        return selectedTransmissions.some(t => transStr.includes(t.toLowerCase()));
      });
    }

    // 7. Seating Capacity
    if (selectedSeatings.length > 0) {
      list = list.filter(v => selectedSeatings.includes(v.specs.seatingCapacity));
    }

    // 8. Price Bracket in INR
    if (priceBracket !== 'all') {
      list = list.filter(v => {
        // Normalize price in INR
        const p = v.currency === 'INR' ? v.startingPrice : (v.startingPrice * 85);
        if (priceBracket === 'under-15l') return p < 1500000;
        if (priceBracket === '15l-30l') return p >= 1500000 && p <= 3000000;
        if (priceBracket === '30l-75l') return p > 3000000 && p <= 7500000;
        if (priceBracket === '75l-2cr') return p > 7500000 && p <= 20000000;
        if (priceBracket === 'above-2cr') return p > 20000000;
        return true;
      });
    }

    // 9. Minimum Power (hp)
    if (minPower > 0) {
      list = list.filter(v => v.specs.maxPowerHp >= minPower);
    }

    // 10. Minimum EV Range (km)
    if (minEvRange > 0) {
      list = list.filter(v => (v.specs.electricRangeKm || 0) >= minEvRange);
    }

    // 11. 3D Model Only
    if (has3DOnly) {
      list = list.filter(v => v.has3D);
    }

    // 12. Blueprint Availability Only
    if (hasBlueprintOnly) {
      list = list.filter(v => Boolean(v.blueprint));
    }

    // 13. Sorting
    switch (sortBy) {
      case 'price-asc':
        list.sort((a, b) => a.startingPrice - b.startingPrice);
        break;
      case 'price-desc':
        list.sort((a, b) => b.startingPrice - a.startingPrice);
        break;
      case 'power-desc':
        list.sort((a, b) => b.specs.maxPowerHp - a.specs.maxPowerHp);
        break;
      case 'accel-asc':
        list.sort((a, b) => a.specs.acceleration0to100Kmh - b.specs.acceleration0to100Kmh);
        break;
      case 'year-desc':
        list.sort((a, b) => b.modelYear - a.modelYear);
        break;
      case 'range-desc':
        list.sort((a, b) => (b.specs.electricRangeKm || 0) - (a.specs.electricRangeKm || 0));
        break;
      case 'popular':
      default:
        list.sort((a, b) => b.viewsCount - a.viewsCount);
        break;
    }

    return list;
  }, [
    searchQuery,
    selectedBrands,
    selectedBodies,
    selectedFuels,
    selectedStatuses,
    selectedTransmissions,
    selectedSeatings,
    priceBracket,
    minPower,
    minEvRange,
    has3DOnly,
    hasBlueprintOnly,
    sortBy,
  ]);

  // Pagination calculation
  const totalResults = filteredVehicles.length;
  const totalPages = Math.ceil(totalResults / pageSize) || 1;
  const paginatedVehicles = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return filteredVehicles.slice(startIndex, startIndex + pageSize);
  }, [filteredVehicles, currentPage]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-surface-border pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
            <span>Official India Automotive Registry</span>
            <span className="text-white/40">•</span>
            <span>Verified Market Homologation</span>
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white font-display mt-1">
            INDIA VEHICLE CATALOGUE
          </h1>
          <p className="text-sm text-white/60 mt-1">
            Explore verified ex-showroom prices, state RTO taxes, engineering blueprints, and interactive 3D models.
          </p>
        </div>

        {/* City Filter / Selector Pill */}
        <div className="flex items-center gap-2 bg-surface-100 p-2 rounded-xl border border-surface-border">
          <MapPin size={16} className="text-cyan-400 shrink-0 ml-1" />
          <span className="text-xs text-white/60">Location:</span>
          <select
            value={selectedCity}
            onChange={(e) => setSelectedCity(e.target.value)}
            className="bg-transparent text-xs font-semibold text-white focus:outline-none cursor-pointer pr-2"
          >
            {INDIAN_CITIES.map((c) => (
              <option key={c.id} value={c.id} className="bg-surface-100 text-white">
                {c.name} ({c.rtoCodePrefix})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Search Bar & Fast Controls */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40" />
          <input
            type="text"
            placeholder="Search by brand, car model, powertrain or body style..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full rounded-xl bg-surface-100 py-3.5 pl-11 pr-10 text-sm text-white placeholder-white/40 border border-surface-border focus:border-cyan-500/50 focus:outline-none shadow-sm"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/40 hover:text-white"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* Sort Select */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="flex-1 sm:flex-initial flex items-center gap-2 rounded-xl bg-surface-100 px-4 py-3 border border-surface-border text-xs font-medium text-white">
            <span className="text-white/50 shrink-0">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-transparent text-white focus:outline-none cursor-pointer"
            >
              <option value="popular" className="bg-surface-100">Most Popular</option>
              <option value="price-asc" className="bg-surface-100">Price: Low to High</option>
              <option value="price-desc" className="bg-surface-100">Price: High to Low</option>
              <option value="power-desc" className="bg-surface-100">Horsepower: High to Low</option>
              <option value="accel-asc" className="bg-surface-100">0-100 km/h: Fastest First</option>
              <option value="range-desc" className="bg-surface-100">EV Range: High to Low</option>
              <option value="year-desc" className="bg-surface-100">Model Year: Newest</option>
            </select>
          </div>

          {/* Mobile Filter Toggle Button */}
          <button
            type="button"
            onClick={() => setMobileFilterOpen(!mobileFilterOpen)}
            className="lg:hidden flex items-center gap-2 rounded-xl bg-cyan-500/10 px-4 py-3 text-xs font-semibold text-cyan-300 border border-cyan-500/30"
          >
            <Filter size={15} />
            <span>Filters</span>
          </button>
        </div>
      </div>

      {/* Active Filter Chips Bar */}
      {hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
          <span className="text-white/40 font-medium">Active Filters:</span>

          {searchQuery && (
            <span className="inline-flex items-center gap-1 rounded-lg bg-surface-100 px-2.5 py-1 text-cyan-300 border border-surface-border">
              <span>"{searchQuery}"</span>
              <button type="button" onClick={() => setSearchQuery('')}><X size={12} /></button>
            </span>
          )}

          {selectedBrands.map((b) => (
            <span key={b} className="inline-flex items-center gap-1 rounded-lg bg-surface-100 px-2.5 py-1 text-cyan-300 border border-surface-border">
              <span>Brand: {BRANDS.find(brand => brand.id === b)?.name || b}</span>
              <button type="button" onClick={() => toggleBrand(b)}><X size={12} /></button>
            </span>
          ))}

          {selectedBodies.map((b) => (
            <span key={b} className="inline-flex items-center gap-1 rounded-lg bg-surface-100 px-2.5 py-1 text-cyan-300 border border-surface-border">
              <span>Body: {b}</span>
              <button type="button" onClick={() => toggleBody(b)}><X size={12} /></button>
            </span>
          ))}

          {selectedFuels.map((f) => (
            <span key={f} className="inline-flex items-center gap-1 rounded-lg bg-surface-100 px-2.5 py-1 text-cyan-300 border border-surface-border">
              <span>Fuel: {f}</span>
              <button type="button" onClick={() => toggleFuel(f)}><X size={12} /></button>
            </span>
          ))}

          {selectedStatuses.map((s) => (
            <span key={s} className="inline-flex items-center gap-1 rounded-lg bg-surface-100 px-2.5 py-1 text-cyan-300 border border-surface-border">
              <span>Status: {s}</span>
              <button type="button" onClick={() => toggleStatus(s)}><X size={12} /></button>
            </span>
          ))}

          {has3DOnly && (
            <span className="inline-flex items-center gap-1 rounded-lg bg-cyan-500/20 px-2.5 py-1 text-cyan-300 border border-cyan-500/40">
              <span>3D Models Only</span>
              <button type="button" onClick={() => setHas3DOnly(false)}><X size={12} /></button>
            </span>
          )}

          {hasBlueprintOnly && (
            <span className="inline-flex items-center gap-1 rounded-lg bg-blue-500/20 px-2.5 py-1 text-blue-300 border border-blue-500/40">
              <span>CAD Blueprints Only</span>
              <button type="button" onClick={() => setHasBlueprintOnly(false)}><X size={12} /></button>
            </span>
          )}

          <button
            type="button"
            onClick={clearAllFilters}
            className="text-white/50 hover:text-white underline ml-2 text-xs"
          >
            Clear All
          </button>
        </div>
      )}

      {/* Main Grid: Multi-Facet Sidebar (Left) + Vehicles Grid (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Desktop Left Filter Sidebar */}
        <aside
          className={`lg:col-span-3 space-y-6 lg:block ${
            mobileFilterOpen ? 'block fixed inset-0 z-50 bg-black/95 p-6 overflow-y-auto' : 'hidden'
          }`}
        >
          <div className="flex items-center justify-between border-b border-surface-border pb-3">
            <div className="flex items-center gap-2 text-sm font-bold text-white">
              <SlidersHorizontal size={16} className="text-cyan-400" />
              <span>Multi-Facet Filters</span>
            </div>
            {mobileFilterOpen && (
              <button
                type="button"
                onClick={() => setMobileFilterOpen(false)}
                className="lg:hidden text-white/60 hover:text-white"
              >
                <X size={20} />
              </button>
            )}
          </div>

          {/* Quick Toggles: 3D & Blueprints */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-white/50 block">
              Digital Assets
            </span>
            <label className="flex items-center justify-between rounded-xl bg-surface-100 p-3 border border-surface-border cursor-pointer hover:bg-surface-50">
              <span className="flex items-center gap-2 text-xs font-semibold text-white">
                <Sparkles size={14} className="text-cyan-400" />
                <span>3D Interactive Models</span>
              </span>
              <input
                type="checkbox"
                checked={has3DOnly}
                onChange={(e) => setHas3DOnly(e.target.checked)}
                className="rounded border-white/20 text-cyan-500 focus:ring-0"
              />
            </label>

            <label className="flex items-center justify-between rounded-xl bg-surface-100 p-3 border border-surface-border cursor-pointer hover:bg-surface-50">
              <span className="flex items-center gap-2 text-xs font-semibold text-white">
                <Compass size={14} className="text-blue-400" />
                <span>CAD Blueprints Available</span>
              </span>
              <input
                type="checkbox"
                checked={hasBlueprintOnly}
                onChange={(e) => setHasBlueprintOnly(e.target.checked)}
                className="rounded border-white/20 text-blue-500 focus:ring-0"
              />
            </label>
          </div>

          {/* India Availability Status */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-white/50 block">
              Market Availability Status
            </span>
            <div className="space-y-1.5">
              {allStatuses.map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => toggleStatus(st)}
                  className={`w-full flex items-center justify-between rounded-lg px-3 py-2 text-xs transition-colors ${
                    selectedStatuses.includes(st)
                      ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40'
                      : 'bg-surface-100 text-white/70 hover:bg-surface-50 hover:text-white border border-surface-border'
                  }`}
                >
                  <span>{st}</span>
                  {selectedStatuses.includes(st) && <Check size={13} />}
                </button>
              ))}
            </div>
          </div>

          {/* Price Range Filter in INR */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-white/50 block">
              Price Bracket (Ex-Showroom)
            </span>
            <div className="space-y-1.5">
              {priceBrackets.map((pb) => (
                <button
                  key={pb.id}
                  type="button"
                  onClick={() => {
                    setPriceBracket(pb.id);
                    setCurrentPage(1);
                  }}
                  className={`w-full text-left rounded-lg px-3 py-2 text-xs transition-colors ${
                    priceBracket === pb.id
                      ? 'bg-cyan-500 text-black font-bold'
                      : 'bg-surface-100 text-white/70 hover:bg-surface-50 hover:text-white border border-surface-border'
                  }`}
                >
                  {pb.label}
                </button>
              ))}
            </div>
          </div>

          {/* Fuel & Powertrain Types */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-white/50 block">
              Powertrain / Fuel
            </span>
            <div className="grid grid-cols-2 gap-1.5">
              {allFuelTypes.map((fuel) => (
                <button
                  key={fuel}
                  type="button"
                  onClick={() => toggleFuel(fuel)}
                  className={`rounded-lg px-2.5 py-1.5 text-xs font-medium text-left transition-colors truncate ${
                    selectedFuels.includes(fuel)
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'bg-surface-100 text-white/70 hover:bg-surface-50 border border-surface-border'
                  }`}
                >
                  {fuel}
                </button>
              ))}
            </div>
          </div>

          {/* Body Styles */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-white/50 block">
              Body Style
            </span>
            <div className="grid grid-cols-2 gap-1.5">
              {allBodyStyles.map((style) => (
                <button
                  key={style}
                  type="button"
                  onClick={() => toggleBody(style)}
                  className={`rounded-lg px-2.5 py-1.5 text-xs font-medium text-left transition-colors truncate ${
                    selectedBodies.includes(style)
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'bg-surface-100 text-white/70 hover:bg-surface-50 border border-surface-border'
                  }`}
                >
                  {style}
                </button>
              ))}
            </div>
          </div>

          {/* Brands */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-white/50 block">
              Manufacturer / Brand
            </span>
            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
              {BRANDS.map((b) => (
                <button
                  key={b.id}
                  type="button"
                  onClick={() => toggleBrand(b.id)}
                  className={`w-full flex items-center justify-between rounded-lg px-3 py-1.5 text-xs transition-colors ${
                    selectedBrands.includes(b.id)
                      ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40'
                      : 'bg-surface-100 text-white/70 hover:bg-surface-50 border border-surface-border'
                  }`}
                >
                  <span>{b.name}</span>
                  {selectedBrands.includes(b.id) && <Check size={12} />}
                </button>
              ))}
            </div>
          </div>

          {/* Seating Capacity */}
          <div className="space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-white/50 block">
              Seating Capacity
            </span>
            <div className="flex gap-2">
              {seatingOptions.map((seats) => (
                <button
                  key={seats}
                  type="button"
                  onClick={() => toggleSeating(seats)}
                  className={`flex-1 rounded-lg py-1.5 text-xs font-medium transition-colors ${
                    selectedSeatings.includes(seats)
                      ? 'bg-cyan-500 text-black font-bold'
                      : 'bg-surface-100 text-white/70 border border-surface-border hover:bg-surface-50'
                  }`}
                >
                  {seats} seats
                </button>
              ))}
            </div>
          </div>

          {/* Minimum Horsepower Slider */}
          <div className="space-y-2 pt-2 border-t border-surface-border">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-white/60">Min Output:</span>
              <span className="font-mono text-cyan-300 font-bold">{minPower} hp</span>
            </div>
            <input
              type="range"
              min="0"
              max="1000"
              step="50"
              value={minPower}
              onChange={(e) => {
                setMinPower(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="w-full accent-cyan-400 cursor-pointer"
            />
          </div>
        </aside>

        {/* Right Vehicles Results Grid (9 Cols) */}
        <main className="lg:col-span-9 space-y-6">
          <div className="flex items-center justify-between text-xs text-white/50">
            <span>
              Showing <strong className="text-white">{filteredVehicles.length}</strong> vehicles in Indian registry
            </span>
            <span>
              Page {currentPage} of {totalPages}
            </span>
          </div>

          {paginatedVehicles.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {paginatedVehicles.map((vehicle) => (
                <CarCard
                  key={vehicle.id}
                  vehicle={vehicle}
                  onQuickView={(v) => setQuickViewVehicle(v)}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-surface-border bg-surface-100 p-12 text-center space-y-4">
              <Car size={40} className="mx-auto text-white/30" />
              <h3 className="text-lg font-bold text-white">No vehicles match your active filters</h3>
              <p className="text-xs text-white/60 max-w-md mx-auto">
                Try widening your price bracket, clearing specific body styles, or resetting filters to see the full Indian catalogue.
              </p>
              <button
                type="button"
                onClick={clearAllFilters}
                className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500 px-5 py-2.5 text-xs font-bold text-black shadow-cyan-glow hover:opacity-90"
              >
                <RotateCcw size={14} />
                <span>Reset All Filters</span>
              </button>
            </div>
          )}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-6 border-t border-surface-border">
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="flex items-center gap-1 rounded-xl bg-surface-100 px-3.5 py-2 text-xs font-medium text-white border border-surface-border disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-50"
              >
                <ChevronLeft size={14} />
                <span>Previous</span>
              </button>

              <div className="flex items-center gap-1">
                {Array.from({ length: totalPages }).map((_, i) => {
                  const pNum = i + 1;
                  return (
                    <button
                      key={pNum}
                      type="button"
                      onClick={() => setCurrentPage(pNum)}
                      className={`h-8 w-8 rounded-lg text-xs font-mono font-semibold transition-colors ${
                        currentPage === pNum
                          ? 'bg-cyan-500 text-black font-bold'
                          : 'bg-surface-100 text-white/70 border border-surface-border hover:bg-surface-50 hover:text-white'
                      }`}
                    >
                      {pNum}
                    </button>
                  );
                })}
              </div>

              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="flex items-center gap-1 rounded-xl bg-surface-100 px-3.5 py-2 text-xs font-medium text-white border border-surface-border disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-50"
              >
                <span>Next</span>
                <ChevronRight size={14} />
              </button>
            </div>
          )}
        </main>
      </div>

      {/* Quick View Modal */}
      {quickViewVehicle && (
        <QuickViewModal
          vehicle={quickViewVehicle}
          onClose={() => setQuickViewVehicle(null)}
        />
      )}
    </div>
  );
}

export default function CarsPage() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-xs text-white/50">Loading India Vehicle Catalogue...</div>}>
      <CarsContent />
    </Suspense>
  );
}

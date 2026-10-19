'use client';

import React, { useState } from 'react';
import { notFound, useParams } from 'next/navigation';
import Link from 'next/link';
import { getVehicleBySlug, VEHICLES } from '@/data/vehicles';
import { BRANDS } from '@/data/brands';
import { VehicleCanvas } from '@/components/3d/VehicleCanvas';
import { BlueprintViewer } from '@/components/cars/BlueprintViewer';
import { PartsExplorer } from '@/components/cars/PartsExplorer';
import { CityPricingCard } from '@/components/cars/CityPricingCard';
import { useStore } from '@/lib/store';
import { formatIndianPrice, formatINRStandard } from '@/lib/pricing';
import { 
  convertSpeed, 
  convertPower, 
  convertTorque, 
  convertRange, 
  convertDimension, 
  convertWeight, 
  convertFuelEconomy,
  formatPrice 
} from '@/lib/units';
import { 
  Sparkles, 
  Scale, 
  Heart, 
  ShieldCheck, 
  ExternalLink, 
  Calendar, 
  CheckCircle2, 
  AlertTriangle, 
  Zap, 
  Gauge, 
  Sliders, 
  Compass, 
  Layers, 
  ArrowLeft,
  Share2,
  Info,
  Car,
  Download,
  Star,
  Clock,
  Wrench,
  Check,
  FileText
} from 'lucide-react';

export default function CarDetailPage() {
  const params = useParams();
  const slug = params?.slug as string;
  const vehicle = getVehicleBySlug(slug);

  if (!vehicle) {
    return notFound();
  }

  const { 
    unitSystem, 
    toggleUnitSystem, 
    isInCompare, 
    toggleCompare, 
    isFavourite, 
    toggleFavourite 
  } = useStore();

  // Active Tab State
  const [activeTab, setActiveTab] = useState<
    'overview' | 'blueprint' | 'parts' | 'pricing' | 'specs' | 'safety' | 'ownership'
  >('overview');

  // Variant Selector State
  const [selectedVariantId, setSelectedVariantId] = useState<string>(
    vehicle.variants[0]?.id || vehicle.variants[0]?.name || ''
  );

  const selectedVariant = vehicle.variants.find(
    v => (v.id && v.id === selectedVariantId) || v.name === selectedVariantId
  ) || vehicle.variants[0];

  const inCompare = isInCompare(vehicle.id);
  const favorited = isFavourite(vehicle.id);
  const brand = BRANDS.find(b => b.id === vehicle.brandId);

  // Dynamic specs based on variant
  const displayPowerHp = selectedVariant?.powerHp || vehicle.specs.maxPowerHp;
  const displayTorqueNm = selectedVariant?.torqueNm || vehicle.specs.maxTorqueNm;
  const displayPrice = selectedVariant?.exShowroomPrice || selectedVariant?.price || vehicle.startingPrice;
  const displayTransmission = selectedVariant?.transmission || vehicle.specs.transmission;

  const tabs = [
    { id: 'overview', label: 'Overview & Highlights' },
    { id: 'blueprint', label: 'Engineering Blueprint', badge: 'CAD' },
    { id: 'parts', label: 'Parts & Subsystems Explorer', badge: 'Tech' },
    { id: 'pricing', label: 'Indian Pricing & On-Road', badge: 'INR' },
    { id: 'specs', label: 'Full Technical Specs' },
    { id: 'safety', label: 'Safety & NCAP Ratings' },
    { id: 'ownership', label: 'Ownership & Warranty' },
  ] as const;

  const handleShare = () => {
    if (typeof navigator !== 'undefined' && navigator.share) {
      navigator.share({
        title: `${vehicle.brandName} ${vehicle.modelName} — AUTOVERSE 3D`,
        url: window.location.href,
      }).catch(() => {});
    } else if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
      alert('Vehicle profile link copied to clipboard!');
    }
  };

  // Status Badge Configuration
  const statusConfig = {
    'Currently Available': { label: 'Officially Available in India', bg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' },
    'Upcoming': { label: 'Upcoming India Launch', bg: 'bg-amber-500/20 text-amber-300 border-amber-500/40' },
    'Imported on Request': { label: 'Imported on Bespoke Request', bg: 'bg-purple-500/20 text-purple-300 border-purple-500/40' },
    'Discontinued': { label: 'Discontinued Production', bg: 'bg-rose-500/20 text-rose-300 border-rose-500/40' },
    'Historical': { label: 'Historical Automotive Landmark', bg: 'bg-blue-500/20 text-blue-300 border-blue-500/40' },
  }[vehicle.indiaAvailabilityStatus || 'Currently Available'];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      {/* Back button & Breadcrumbs */}
      <div className="flex items-center justify-between text-xs text-white/50">
        <Link
          href="/cars"
          className="inline-flex items-center gap-1.5 hover:text-cyan-400 transition-colors"
        >
          <ArrowLeft size={14} />
          <span>Back to All Vehicles</span>
        </Link>

        <div className="flex items-center gap-2">
          <Link href="/cars" className="hover:text-white">India Catalogue</Link>
          <span>/</span>
          <Link href={`/brands/${vehicle.brandId}`} className="hover:text-white">{vehicle.brandName}</Link>
          <span>/</span>
          <span className="text-cyan-400 font-medium">{vehicle.modelName}</span>
        </div>
      </div>

      {/* ========================================================= */}
      {/* HEADER SECTION */}
      {/* ========================================================= */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 border-b border-surface-border pb-8">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Link
              href={`/brands/${vehicle.brandId}`}
              className="font-bold text-cyan-400 uppercase tracking-wider hover:underline"
            >
              {vehicle.brandName}
            </Link>
            <span className="text-white/30">•</span>
            <span className="text-white/70">{vehicle.modelYear}</span>
            <span className="text-white/30">•</span>
            <span className="text-white/70">{vehicle.generationAndFacelift || vehicle.generation}</span>
            <span className="text-white/30">•</span>
            <span className="rounded-md bg-surface-100 px-2.5 py-0.5 text-white/80 border border-surface-border">
              {vehicle.bodyStyle}
            </span>
            <span className="rounded-md bg-cyan-500/10 px-2.5 py-0.5 text-cyan-300 border border-cyan-500/30">
              {vehicle.fuelType}
            </span>
            <span className={`rounded-md px-2.5 py-0.5 border ${statusConfig.bg}`}>
              {statusConfig.label}
            </span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white font-display tracking-tight">
            {vehicle.modelName}
          </h1>

          <p className="text-base text-white/70 max-w-2xl leading-relaxed">
            {vehicle.tagline}
          </p>
        </div>

        {/* Pricing & Fast Actions */}
        <div className="flex flex-col sm:flex-row lg:flex-col items-start lg:items-end justify-between gap-4 shrink-0">
          <div className="text-left lg:text-right">
            <span className="text-xs uppercase tracking-wider text-white/40 block">
              {selectedVariant ? `${selectedVariant.trim} Ex-Showroom` : `Starting ${vehicle.priceType}`}
            </span>
            <span className="text-3xl sm:text-4xl font-extrabold text-white font-mono">
              {formatIndianPrice(displayPrice)}
            </span>
            <span className="text-[11px] text-white/40 block mt-0.5">
              Verified with ARAI / OEM registry: {vehicle.lastAvailabilityVerificationDate || vehicle.verificationDate}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => toggleCompare(vehicle.id)}
              className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-semibold border transition-all ${
                inCompare
                  ? 'bg-cyan-500 border-cyan-400 text-black shadow-cyan-glow'
                  : 'bg-surface-100 border-surface-border text-white hover:bg-surface-50'
              }`}
            >
              <Scale size={15} />
              <span>{inCompare ? 'Comparing' : 'Compare'}</span>
            </button>

            <button
              type="button"
              onClick={() => toggleFavourite(vehicle.id)}
              className={`flex items-center justify-center rounded-xl p-2.5 border transition-all ${
                favorited
                  ? 'bg-red-500/20 border-red-500 text-red-400'
                  : 'bg-surface-100 border-surface-border text-white hover:bg-surface-50'
              }`}
              title={favorited ? 'Remove from favourites' : 'Save to favourites'}
            >
              <Heart size={16} className={favorited ? 'fill-red-400' : ''} />
            </button>

            <button
              type="button"
              onClick={handleShare}
              className="flex items-center justify-center rounded-xl p-2.5 bg-surface-100 border border-surface-border text-white hover:bg-surface-50"
              title="Share car profile"
            >
              <Share2 size={16} />
            </button>

            {vehicle.officialBrochureUrl && (
              <a
                href={vehicle.officialBrochureUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 rounded-xl bg-surface-100 px-3.5 py-2.5 text-xs font-medium text-white/70 hover:text-white border border-surface-border hover:bg-surface-50"
                title="Download Official Indian Manufacturer Brochure"
              >
                <Download size={14} className="text-cyan-400" />
                <span className="hidden sm:inline">Brochure</span>
              </a>
            )}

            {vehicle.officialUrl && (
              <a
                href={vehicle.officialUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 rounded-xl bg-surface-100 px-3.5 py-2.5 text-xs font-medium text-white/70 hover:text-white border border-surface-border hover:bg-surface-50"
              >
                <span>Official OEM</span>
                <ExternalLink size={13} />
              </a>
            )}
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 3D INTERACTIVE CAR VIEWER SHOWCASE */}
      {/* ========================================================= */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-400">
            <Sparkles size={14} />
            <span>Interactive 3D Vehicle Studio & Engineering Inspection</span>
          </div>
          <div className="flex items-center gap-3 text-xs text-white/50">
            <span>Asset: <strong className="text-white/80">{vehicle.asset3DMetadata?.verificationStatus || 'Certified Geometry'}</strong></span>
            <span>•</span>
            <span>Scale: 1:1 Real Proportions</span>
          </div>
        </div>

        <VehicleCanvas vehicle={vehicle} />
      </section>

      {/* ========================================================= */}
      {/* QUICK METRICS STRIP (UPDATES WITH VARIANT SELECTION) */}
      {/* ========================================================= */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-2xl bg-surface-100 p-5 border border-surface-border">
          <span className="text-xs uppercase tracking-wider text-white/40 block">Max Output</span>
          <span className="text-2xl font-bold text-white font-mono mt-1 block">
            {displayPowerHp} hp
          </span>
          <span className="text-[11px] text-white/50 mt-1 block">
            Torque: {displayTorqueNm} Nm
          </span>
        </div>

        <div className="rounded-2xl bg-surface-100 p-5 border border-surface-border">
          <span className="text-xs uppercase tracking-wider text-white/40 block">Transmission</span>
          <span className="text-lg font-bold text-cyan-300 font-mono mt-1 block truncate">
            {displayTransmission}
          </span>
          <span className="text-[11px] text-white/50 mt-1 block">
            Drivetrain: {vehicle.specs.driveType}
          </span>
        </div>

        <div className="rounded-2xl bg-surface-100 p-5 border border-surface-border">
          <span className="text-xs uppercase tracking-wider text-white/40 block">
            {vehicle.fuelType === 'Electric' ? 'Claimed Range' : 'Fuel Economy'}
          </span>
          <span className="text-2xl font-bold text-white font-mono mt-1 block">
            {selectedVariant?.claimedMileageOrRange || (
              vehicle.fuelType === 'Electric'
                ? convertRange(vehicle.specs.electricRangeKm, unitSystem)
                : vehicle.specs.fuelEconomyKmPerL 
                ? `${vehicle.specs.fuelEconomyKmPerL} km/L`
                : 'Verified Cycle'
            )}
          </span>
          <span className="text-[11px] text-white/50 mt-1 block">
            Homologation: {vehicle.specs.rangeTestCycle || 'ARAI / MIDC'}
          </span>
        </div>

        <div className="rounded-2xl bg-surface-100 p-5 border border-surface-border">
          <span className="text-xs uppercase tracking-wider text-white/40 block">Safety Rating</span>
          <span className="text-2xl font-bold text-amber-300 font-mono mt-1 block flex items-center gap-1.5">
            <Star size={20} className="fill-amber-300" />
            <span>{vehicle.specs.ncapRating ? `${vehicle.specs.ncapRating} Stars` : 'Safety Cage'}</span>
          </span>
          <span className="text-[11px] text-white/50 mt-1 block">
            {vehicle.specs.ncapAgency || 'Bharat NCAP'} ({vehicle.specs.ncapYear || 2024})
          </span>
        </div>
      </div>

      {/* ========================================================= */}
      {/* SECTION TABS NAVIGATION */}
      {/* ========================================================= */}
      <div className="border-b border-surface-border overflow-x-auto pb-1">
        <nav className="flex items-center gap-2 sm:gap-3 min-w-max">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 rounded-xl px-4 py-3 text-xs sm:text-sm font-semibold transition-all relative ${
                  isActive
                    ? 'text-cyan-300 bg-cyan-500/10 border border-cyan-500/40 shadow-sm'
                    : 'text-white/60 hover:text-white hover:bg-surface-100 border border-transparent'
                }`}
              >
                <span>{tab.label}</span>
                {'badge' in tab && (
                  <span className="rounded bg-cyan-500/20 px-1.5 py-0.2 text-[10px] font-mono text-cyan-300">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* ========================================================= */}
      {/* TAB CONTENT A: OVERVIEW & VARIANT SELECTOR */}
      {/* ========================================================= */}
      {activeTab === 'overview' && (
        <div className="space-y-10 animate-fadeIn">
          {/* Variant Selector Matrix */}
          <div className="rounded-2xl border border-surface-border bg-surface-100 p-6 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Sliders size={18} className="text-cyan-400" />
                  <span>Choose Model Variant / Trim</span>
                </h3>
                <p className="text-xs text-white/60">
                  Select a trim to see exact variant-level ex-showroom pricing, standard equipment, and specifications.
                </p>
              </div>
              <span className="text-xs text-cyan-400 font-mono">
                {vehicle.variants.length} Trims Available in India
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {vehicle.variants.map((v) => {
                const isSelected = selectedVariant.id === v.id || selectedVariant.name === v.name;
                const vPrice = v.exShowroomPrice || v.price;
                return (
                  <button
                    key={v.id || v.name}
                    type="button"
                    onClick={() => setSelectedVariantId(v.id || v.name)}
                    className={`text-left rounded-xl p-4 border transition-all ${
                      isSelected
                        ? 'bg-cyan-950/40 border-cyan-500 shadow-cyan-glow'
                        : 'bg-surface-200/50 border-surface-border hover:bg-surface-50 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <span className="text-xs font-bold text-white leading-snug">
                        {v.name}
                      </span>
                      {isSelected && (
                        <span className="h-2 w-2 rounded-full bg-cyan-400 shrink-0 mt-1" />
                      )}
                    </div>

                    <div className="flex items-baseline justify-between text-xs mt-3">
                      <span className="text-white/50">{v.transmission}</span>
                      <span className="font-extrabold text-cyan-300 font-mono text-sm">
                        {formatIndianPrice(vPrice)}
                      </span>
                    </div>

                    {v.keyFeatures && v.keyFeatures.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-white/5 flex flex-wrap gap-1">
                        {v.keyFeatures.slice(0, 3).map((f, i) => (
                          <span
                            key={i}
                            className="rounded bg-surface-100 px-2 py-0.5 text-[10px] text-white/70"
                          >
                            {f}
                          </span>
                        ))}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Overview Prose */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div className="lg:col-span-8 space-y-4">
              <h3 className="text-xl font-bold text-white">Engineering Overview</h3>
              <p className="text-sm text-white/80 leading-relaxed bg-surface-100 p-6 rounded-2xl border border-surface-border">
                {vehicle.overviewDescription}
              </p>

              {/* Exterior Highlights */}
              <div className="space-y-3 pt-4">
                <h4 className="text-sm font-bold uppercase tracking-wider text-cyan-400">
                  Key Exterior Innovations
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {vehicle.exteriorHighlights.map((highlight, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-2.5 rounded-xl bg-surface-100 p-3.5 border border-surface-border text-xs text-white/80"
                    >
                      <CheckCircle2 size={16} className="text-cyan-400 shrink-0 mt-0.5" />
                      <span>{highlight}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Interior Highlights */}
              <div className="space-y-3 pt-4">
                <h4 className="text-sm font-bold uppercase tracking-wider text-cyan-400">
                  Interior & Cockpit Architecture
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {vehicle.interiorHighlights.map((highlight, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-2.5 rounded-xl bg-surface-100 p-3.5 border border-surface-border text-xs text-white/80"
                    >
                      <Sparkles size={16} className="text-cyan-400 shrink-0 mt-0.5" />
                      <span>{highlight}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Strengths & Limitations Sidebar */}
            <div className="lg:col-span-4 space-y-6">
              {/* Strengths */}
              <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/10 p-5 space-y-3">
                <div className="flex items-center gap-2 text-emerald-400">
                  <CheckCircle2 size={18} />
                  <h4 className="text-sm font-bold uppercase tracking-wider">Key Strengths</h4>
                </div>
                <ul className="space-y-2.5 text-xs text-white/80">
                  {vehicle.keyStrengths.map((strength, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-emerald-400 font-bold">•</span>
                      <span>{strength}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Limitations */}
              <div className="rounded-2xl border border-amber-500/30 bg-amber-950/10 p-5 space-y-3">
                <div className="flex items-center gap-2 text-amber-400">
                  <AlertTriangle size={18} />
                  <h4 className="text-sm font-bold uppercase tracking-wider">Considerations & Limitations</h4>
                </div>
                <ul className="space-y-2.5 text-xs text-white/80">
                  {vehicle.limitations.map((limit, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-amber-400 font-bold">•</span>
                      <span>{limit}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB CONTENT B: ENGINEERING BLUEPRINT MODE */}
      {/* ========================================================= */}
      {activeTab === 'blueprint' && (
        <div className="space-y-4 animate-fadeIn">
          <BlueprintViewer vehicle={vehicle} />
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB CONTENT C: PARTS & SUBSYSTEMS EXPLORER */}
      {/* ========================================================= */}
      {activeTab === 'parts' && (
        <div className="space-y-4 animate-fadeIn">
          <PartsExplorer vehicle={vehicle} />
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB CONTENT D: INDIAN PRICING & ON-ROAD CALCULATOR */}
      {/* ========================================================= */}
      {activeTab === 'pricing' && (
        <div className="space-y-6 animate-fadeIn">
          <CityPricingCard vehicle={vehicle} selectedVariant={selectedVariant} />
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB CONTENT E: FULL TECHNICAL SPECIFICATIONS TABLE */}
      {/* ========================================================= */}
      {activeTab === 'specs' && (
        <div className="space-y-8 animate-fadeIn">
          {/* Powertrain Specifications */}
          <div className="rounded-2xl border border-surface-border bg-surface-100 p-6 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Zap size={18} className="text-cyan-400" />
              <span>Powertrain & Mechanical Specifications</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
              <SpecItem label="Fuel & Energy Type" value={vehicle.fuelType} />
              <SpecItem label="Engine Configuration" value={vehicle.specs.engineConfiguration || 'Electric High-Voltage Motor'} />
              <SpecItem label="Displacement" value={vehicle.specs.engineDisplacementCc ? `${vehicle.specs.engineDisplacementCc} cc` : 'N/A (Pure EV)'} />
              <SpecItem label="Peak Horsepower" value={`${displayPowerHp} hp (${Math.round(displayPowerHp * 0.735499)} kW)`} highlight />
              <SpecItem label="Maximum Torque" value={`${displayTorqueNm} Nm`} highlight />
              <SpecItem label="Transmission" value={displayTransmission} />
              <SpecItem label="Drivetrain Layout" value={vehicle.specs.driveType} />
              <SpecItem label="0 to 100 km/h Sprint" value={`${vehicle.specs.acceleration0to100Kmh} seconds`} highlight />
              <SpecItem label="Top Speed" value={convertSpeed(vehicle.specs.topSpeedKmh, unitSystem)} />
              <SpecItem label="Emissions Standard" value={vehicle.specs.emissionsStandard || 'Zero Direct Tailpipe Emissions'} />
            </div>
          </div>

          {/* Electric Vehicle Specifications if EV */}
          {vehicle.fuelType === 'Electric' && (
            <div className="rounded-2xl border border-surface-border bg-surface-100 p-6 space-y-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Sparkles size={18} className="text-cyan-400" />
                <span>Electric Skateboard & Battery Architecture</span>
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
                <SpecItem label="Battery Pack Capacity" value={`${vehicle.specs.batteryCapacityKwh} kWh`} highlight />
                <SpecItem label="Claimed Driving Range" value={`${vehicle.specs.electricRangeKm} km (${vehicle.specs.rangeTestCycle || 'ARAI'})`} highlight />
                <SpecItem label="Max DC Fast Charge" value={`${vehicle.specs.maxDcChargingPowerKw} kW`} />
                <SpecItem label="DC Fast Charge (10-80%)" value={`${vehicle.specs.dcChargingTime10to80Min} minutes`} />
                <SpecItem label="AC Home Charging (0-100%)" value={`${vehicle.specs.acChargingTime0to100Hours} hours`} />
                <SpecItem label="Charging Connector Standard" value={vehicle.specs.chargingConnector || 'CCS Type 2'} />
                <SpecItem label="Battery Warranty" value={`${vehicle.specs.batteryWarrantyYears || 8} Years / ${vehicle.specs.batteryWarrantyKm?.toLocaleString() || '1,60,000'} km`} highlight />
              </div>
            </div>
          )}

          {/* Dimensions & Capacities */}
          <div className="rounded-2xl border border-surface-border bg-surface-100 p-6 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Compass size={18} className="text-cyan-400" />
              <span>Dimensions, Capacities & Weight</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
              <SpecItem label="Overall Length" value={convertDimension(vehicle.specs.lengthMm, unitSystem)} />
              <SpecItem label="Overall Width" value={convertDimension(vehicle.specs.widthMm, unitSystem)} />
              <SpecItem label="Overall Height" value={convertDimension(vehicle.specs.heightMm, unitSystem)} />
              <SpecItem label="Wheelbase" value={convertDimension(vehicle.specs.wheelbaseMm, unitSystem)} />
              <SpecItem label="Ground Clearance" value={convertDimension(vehicle.specs.groundClearanceMm, unitSystem)} highlight />
              <SpecItem label="Kerb Weight" value={convertWeight(vehicle.specs.kerbWeightKg, unitSystem)} />
              <SpecItem label="Boot Capacity" value={`${vehicle.specs.bootCapacityLiters} Liters`} />
              <SpecItem label="Seating Capacity" value={`${vehicle.specs.seatingCapacity} Passengers`} />
              <SpecItem label="Tyre Sizes (Front/Rear)" value={vehicle.specs.frontTyres} />
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB CONTENT F: SAFETY & BHARAT NCAP */}
      {/* ========================================================= */}
      {activeTab === 'safety' && (
        <div className="space-y-6 animate-fadeIn">
          <div className="rounded-2xl border border-surface-border bg-surface-100 p-6 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-5">
              <div>
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <ShieldCheck size={22} className="text-emerald-400" />
                  <span>Crash Test Ratings & Structural Protection</span>
                </h3>
                <p className="text-xs text-white/60">
                  Certified crash test scores evaluated under Bharat NCAP / Global NCAP protocols.
                </p>
              </div>

              {vehicle.specs.ncapRating && (
                <div className="flex items-center gap-2 rounded-xl bg-amber-500/10 px-4 py-2 border border-amber-500/30">
                  <div className="flex items-center gap-1">
                    {Array.from({ length: vehicle.specs.ncapRating }).map((_, i) => (
                      <Star key={i} size={16} className="fill-amber-300 text-amber-300" />
                    ))}
                  </div>
                  <span className="text-xs font-bold text-amber-300">
                    {vehicle.specs.ncapRating}-Star {vehicle.specs.ncapAgency}
                  </span>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div className="rounded-xl bg-surface-200/50 p-4 border border-surface-border space-y-1">
                <span className="text-white/50 block">Airbags Count</span>
                <span className="text-xl font-bold text-white font-mono">{vehicle.specs.airbagsCount} Airbags</span>
                <p className="text-[11px] text-white/60">Dual front, side torso, and full curtain airbags standard</p>
              </div>

              <div className="rounded-xl bg-surface-200/50 p-4 border border-surface-border space-y-1">
                <span className="text-white/50 block">Active Braking & ESC</span>
                <span className="text-xl font-bold text-white font-mono">ABS + ESC 9.3</span>
                <p className="text-[11px] text-white/60">Includes Electronic Brake Distribution & Roll-over mitigation</p>
              </div>

              <div className="rounded-xl bg-surface-200/50 p-4 border border-surface-border space-y-1">
                <span className="text-white/50 block">ADAS Autonomous Tech</span>
                <span className="text-xl font-bold text-cyan-300 font-mono">{vehicle.specs.adasLevel}</span>
                <p className="text-[11px] text-white/60">{vehicle.specs.adasFeatures.length} Active Safety Radar & Vision Features</p>
              </div>
            </div>

            {vehicle.specs.adasFeatures.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-400">
                  Advanced Driver Assistance Systems (ADAS) Feature Suite
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {vehicle.specs.adasFeatures.map((feat, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 rounded-lg bg-surface-200/40 px-3.5 py-2.5 border border-surface-border text-xs text-white/80"
                    >
                      <CheckCircle2 size={14} className="text-cyan-400 shrink-0" />
                      <span>{feat}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB CONTENT G: OWNERSHIP & WARRANTY */}
      {/* ========================================================= */}
      {activeTab === 'ownership' && (
        <div className="space-y-6 animate-fadeIn">
          <div className="rounded-2xl border border-surface-border bg-surface-100 p-6 space-y-6">
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              <Wrench size={20} className="text-cyan-400" />
              <span>Manufacturer Warranty & Scheduled Maintenance</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div className="rounded-xl bg-surface-200/50 p-4 border border-surface-border space-y-1">
                <span className="text-white/50 block">Standard Vehicle Warranty</span>
                <span className="text-xl font-bold text-white font-mono">
                  {vehicle.specs.warrantyYears} Years / {vehicle.specs.warrantyKilometers.toLocaleString()} km
                </span>
                <p className="text-[11px] text-white/60">Bumper-to-bumper factory warranty with roadside assistance</p>
              </div>

              <div className="rounded-xl bg-surface-200/50 p-4 border border-surface-border space-y-1">
                <span className="text-white/50 block">Estimated Annual Service Cost</span>
                <span className="text-xl font-bold text-cyan-300 font-mono">
                  ₹{vehicle.specs.estimatedAnnualServiceCost.toLocaleString('en-IN')} / Year
                </span>
                <p className="text-[11px] text-white/60">Estimated routine scheduled inspection and consumable charges</p>
              </div>

              <div className="rounded-xl bg-surface-200/50 p-4 border border-surface-border space-y-1">
                <span className="text-white/50 block">Service Interval</span>
                <span className="text-xl font-bold text-white font-mono">
                  {vehicle.specs.serviceIntervalKm || 10000} km / {vehicle.specs.serviceIntervalMonths || 12} Mo
                </span>
                <p className="text-[11px] text-white/60">Routine periodic maintenance schedule at authorized dealer</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* DATA SOURCES & GOVERNANCE AUDIT FOOTER */}
      {/* ========================================================= */}
      <div className="rounded-2xl border border-surface-border bg-surface-100/50 p-6 space-y-4 text-xs">
        <div className="flex items-center justify-between border-b border-surface-border pb-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-400" />
            <h4 className="font-bold text-white">Data Authenticity & Verification Governance</h4>
          </div>
          <span className="text-[11px] text-white/50 font-mono">
            Audited by: {vehicle.verifiedBy}
          </span>
        </div>

        <p className="text-xs text-white/70 leading-relaxed">
          AUTOVERSE 3D strictly adheres to authenticated automotive data governance. Specifications, dimensions, and homologation figures are verified against official manufacturer press kits, Ministry of Road Transport & Highways (MoRTH) Form 22 certificates, and authorized crash testing records.
        </p>

        <div className="space-y-2 pt-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-white/40 block">
            Primary Data References:
          </span>
          <div className="flex flex-wrap gap-3">
            {vehicle.sources.map((src, i) => (
              <a
                key={i}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg bg-surface-200 px-3 py-1.5 text-xs text-cyan-300 hover:text-white border border-surface-border hover:border-cyan-500/40 transition-colors"
              >
                <span>{src.title}</span>
                <ExternalLink size={11} />
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SpecItem({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string | number;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-xl bg-surface-200/50 p-3.5 border border-surface-border space-y-1">
      <span className="text-[11px] text-white/50 uppercase tracking-wider block">
        {label}
      </span>
      <span
        className={`text-sm font-bold font-mono block ${
          highlight ? 'text-cyan-300 font-extrabold' : 'text-white'
        }`}
      >
        {value}
      </span>
    </div>
  );
}

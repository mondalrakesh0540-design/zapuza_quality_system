'use client';

import React, { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { VEHICLES } from '@/data/vehicles';
import { Vehicle, VehicleVariant } from '@/types/vehicle';
import { useStore } from '@/lib/store';
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
  INDIAN_CITIES, 
  calculateCityOnRoadPrice, 
  formatIndianPrice, 
  formatINRStandard 
} from '@/lib/pricing';
import { 
  Scale, 
  Plus, 
  X, 
  Sparkles, 
  Check, 
  ShieldCheck, 
  Share2, 
  ArrowRight,
  RotateCcw,
  SlidersHorizontal,
  Car,
  MapPin,
  FileText,
  BadgeCheck,
  Compass,
  ExternalLink
} from 'lucide-react';

function CompareContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { 
    comparisonIds, 
    addToCompare, 
    removeFromCompare, 
    clearCompare, 
    unitSystem 
  } = useStore();

  const [highlightDifferences, setHighlightDifferences] = useState(true);
  const [onlyDifferences, setOnlyDifferences] = useState(false);
  const [pickerSlotIndex, setPickerSlotIndex] = useState<number | null>(null);
  const [selectedCityId, setSelectedCityId] = useState<string>('delhi');
  const [selectedVariantIds, setSelectedVariantIds] = useState<Record<string, string>>({});

  // Sync URL query params with store and city
  useEffect(() => {
    const urlCars = searchParams.get('cars');
    const urlCity = searchParams.get('city');

    if (urlCity && INDIAN_CITIES.some(c => c.id === urlCity)) {
      setSelectedCityId(urlCity);
    }

    if (urlCars) {
      const ids = urlCars.split(',').filter(Boolean);
      ids.forEach(id => {
        if (VEHICLES.some(v => v.id === id) && !comparisonIds.includes(id)) {
          addToCompare(id);
        }
      });
    } else if (comparisonIds.length > 0) {
      const params = new URLSearchParams();
      params.set('cars', comparisonIds.join(','));
      params.set('city', selectedCityId);
      router.replace(`/compare?${params.toString()}`);
    }
  }, [comparisonIds]);

  // Update URL when city changes
  const handleCityChange = (cityId: string) => {
    setSelectedCityId(cityId);
    const params = new URLSearchParams(window.location.search);
    params.set('city', cityId);
    if (comparisonIds.length > 0) {
      params.set('cars', comparisonIds.join(','));
    }
    router.replace(`/compare?${params.toString()}`);
  };

  // If no vehicles are selected, provide 2 default ones for instant demo
  const activeIds = comparisonIds.length > 0 ? comparisonIds : ['porsche-911-gt3-rs', 'tata-nexon-ev'];
  const cars = activeIds
    .map(id => VEHICLES.find(v => v.id === id))
    .filter(Boolean) as Vehicle[];

  const handleShare = () => {
    const params = new URLSearchParams();
    params.set('cars', (comparisonIds.length > 0 ? comparisonIds : activeIds).join(','));
    params.set('city', selectedCityId);
    const shareUrl = `${window.location.origin}/compare?${params.toString()}`;

    if (navigator.clipboard) {
      navigator.clipboard.writeText(shareUrl);
      alert('Matrix link with selected vehicles and city copied to clipboard!');
    }
  };

  // Helper to get active variant for a car
  const getActiveVariant = (car: Vehicle): VehicleVariant | undefined => {
    if (!car.variants || car.variants.length === 0) return undefined;
    const selectedId = selectedVariantIds[car.id];
    return car.variants.find(v => v.id === selectedId) || car.variants[0];
  };

  const handleVariantChange = (carId: string, variantId: string) => {
    setSelectedVariantIds(prev => ({ ...prev, [carId]: variantId }));
  };

  const currentCity = INDIAN_CITIES.find(c => c.id === selectedCityId) || INDIAN_CITIES[0];

  // Helper to calculate on-road price for car in selected city
  const getCarPricing = (car: Vehicle) => {
    const variant = getActiveVariant(car);
    const exShowroom = variant?.exShowroomPrice || variant?.price || car.startingPrice;
    const fuel = variant?.fuelType || car.fuelType;
    return calculateCityOnRoadPrice(
      exShowroom,
      fuel,
      selectedCityId,
      variant?.sourceUrl || car.officialUrl || 'https://parivahan.gov.in',
      variant?.lastVerifiedDate || car.verificationDate
    );
  };

  // Difference detection helper
  const isDifferent = (getter: (car: Vehicle) => any) => {
    if (cars.length < 2) return false;
    const firstVal = getter(cars[0]);
    return cars.some(c => getter(c) !== firstVal);
  };

  const renderRow = (
    label: string,
    getter: (car: Vehicle) => React.ReactNode,
    unitTransform?: (car: Vehicle) => string
  ) => {
    const different = isDifferent(car => unitTransform ? unitTransform(car) : getter(car));
    if (onlyDifferences && !different) return null;

    return (
      <tr className={`border-b border-surface-border text-xs transition-colors ${
        highlightDifferences && different ? 'bg-cyan-500/5' : ''
      }`}>
        <td className="py-3 px-4 font-medium text-white/50 w-56 shrink-0">
          <div className="flex items-center gap-1.5">
            <span>{label}</span>
            {highlightDifferences && different && (
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" title="Values differ" />
            )}
          </div>
        </td>
        {cars.map((car) => (
          <td key={car.id} className="py-3 px-4 font-mono font-bold text-white">
            {unitTransform ? unitTransform(car) : getter(car)}
          </td>
        ))}
        {/* Fill empty slots up to 4 */}
        {Array.from({ length: Math.max(0, 4 - cars.length) }).map((_, i) => (
          <td key={i} className="py-3 px-4 text-white/20">—</td>
        ))}
      </tr>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 border-b border-surface-border pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
            <Scale size={14} />
            <span>Multi-Vehicle Evaluation Matrix</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white font-display mt-1">
            Compare Vehicles
          </h1>
          <p className="text-sm text-white/60 mt-1 max-w-2xl">
            Analyze variant-level specifications, verified Indian ex-showroom & on-road pricing, real RTO tax slabs, dimensions, and engineering blueprints side-by-side.
          </p>
        </div>

        {/* Global Controls & City Selector */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Indian City Selector */}
          <div className="flex items-center gap-2 rounded-xl bg-surface-100 px-3 py-2 border border-cyan-500/40 text-xs text-white shadow-sm">
            <MapPin size={14} className="text-cyan-400 shrink-0" />
            <span className="text-[11px] text-white/50 font-bold uppercase">City:</span>
            <select
              value={selectedCityId}
              onChange={(e) => handleCityChange(e.target.value)}
              className="bg-transparent text-white font-bold focus:outline-none cursor-pointer"
            >
              {INDIAN_CITIES.map((c) => (
                <option key={c.id} value={c.id} className="bg-surface-100 text-white">
                  {c.name} ({c.state})
                </option>
              ))}
            </select>
          </div>

          {/* Highlight toggle */}
          <button
            type="button"
            onClick={() => setHighlightDifferences(!highlightDifferences)}
            className={`rounded-xl px-3 py-2 text-xs font-semibold border transition-all ${
              highlightDifferences
                ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                : 'bg-surface-100 border-surface-border text-white/60'
            }`}
          >
            Highlight Differences
          </button>

          {/* Only differences toggle */}
          <button
            type="button"
            onClick={() => setOnlyDifferences(!onlyDifferences)}
            className={`rounded-xl px-3 py-2 text-xs font-semibold border transition-all ${
              onlyDifferences
                ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                : 'bg-surface-100 border-surface-border text-white/60'
            }`}
          >
            Only Differences
          </button>

          {/* Share button */}
          <button
            type="button"
            onClick={handleShare}
            className="flex items-center gap-1.5 rounded-xl bg-surface-100 px-3 py-2 text-xs font-semibold text-white border border-surface-border hover:bg-surface-50"
          >
            <Share2 size={13} />
            <span>Share Matrix</span>
          </button>

          {/* Reset button */}
          <button
            type="button"
            onClick={clearCompare}
            className="flex items-center gap-1.5 rounded-xl bg-surface-100 px-3 py-2 text-xs font-semibold text-white/60 hover:text-white border border-surface-border"
          >
            <RotateCcw size={13} />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* ========================================================= */}
      {/* COMPARISON MATRIX TABLE */}
      {/* ========================================================= */}
      <div className="rounded-3xl bg-surface-100 border border-surface-border overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[800px]">
            {/* Header row with vehicle cards */}
            <thead>
              <tr className="border-b border-surface-border bg-surface-200/50">
                <th className="p-4 align-top w-56 shrink-0">
                  <span className="text-xs uppercase tracking-wider text-white/40 font-bold block">
                    Specification Matrix
                  </span>
                  <span className="text-[11px] text-white/50 block mt-1">
                    Up to 4 vehicles side-by-side
                  </span>
                  <span className="inline-block mt-2 rounded bg-cyan-500/10 px-2 py-0.5 text-[10px] font-bold text-cyan-300 border border-cyan-500/20">
                    Pricing Location: {currentCity.name}
                  </span>
                </th>

                {cars.map((car) => {
                  const activeVariant = getActiveVariant(car);
                  const pricing = getCarPricing(car);

                  return (
                    <th key={car.id} className="p-4 align-top w-64 min-w-[240px]">
                      <div className="relative rounded-2xl bg-surface-100 p-3 border border-surface-border space-y-3">
                        <button
                          type="button"
                          onClick={() => removeFromCompare(car.id)}
                          className="absolute top-2 right-2 rounded-full bg-black/60 p-1 text-white/60 hover:text-red-400 z-10"
                          title="Remove from comparison"
                        >
                          <X size={14} />
                        </button>

                        <div className="relative rounded-xl overflow-hidden h-28 w-full bg-surface-200">
                          <img
                            src={car.heroImage}
                            alt={car.modelName}
                            className="h-full w-full object-cover"
                          />
                          {car.availabilityStatus && (
                            <span className="absolute bottom-1.5 left-1.5 rounded bg-black/70 backdrop-blur-sm px-1.5 py-0.5 text-[9px] font-bold text-cyan-300 border border-cyan-500/30">
                              {car.availabilityStatus}
                            </span>
                          )}
                        </div>

                        <div>
                          <span className="text-[10px] font-bold text-cyan-400 uppercase">
                            {car.brandName}
                          </span>
                          <Link href={`/cars/${car.slug}`}>
                            <h3 className="text-sm font-bold text-white hover:text-cyan-300 transition-colors truncate">
                              {car.modelName}
                            </h3>
                          </Link>

                          {/* Variant Selector */}
                          {car.variants && car.variants.length > 0 && (
                            <div className="mt-2">
                              <label className="text-[10px] text-white/50 uppercase font-semibold block mb-0.5">
                                Select Variant:
                              </label>
                              <select
                                value={activeVariant?.id}
                                onChange={(e) => handleVariantChange(car.id, e.target.value)}
                                className="w-full rounded-lg bg-surface-200 px-2 py-1 text-[11px] font-medium text-white border border-surface-border focus:border-cyan-400 focus:outline-none"
                              >
                                {car.variants.map((v) => (
                                  <option key={v.id} value={v.id} className="bg-surface-100 text-white">
                                    {v.trim || v.name} ({formatIndianPrice(v.exShowroomPrice || v.price)})
                                  </option>
                                ))}
                              </select>
                            </div>
                          )}

                          <div className="mt-2 pt-2 border-t border-surface-border/60">
                            <span className="text-[10px] text-white/50 block">Ex-Showroom Price:</span>
                            <span className="text-xs font-extrabold text-white font-mono block">
                              {formatIndianPrice(activeVariant?.exShowroomPrice || activeVariant?.price || car.startingPrice)}
                            </span>
                            <span className="text-[10px] text-cyan-400 font-bold block mt-0.5">
                              Est. On-Road ({currentCity.name}): {formatIndianPrice(pricing.totalOnRoadEstimate)}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5 pt-1">
                          <Link
                            href={`/cars/${car.slug}`}
                            className="flex-1 text-center rounded-lg bg-surface-200 py-1.5 text-[11px] font-semibold text-white hover:bg-surface-50 border border-surface-border"
                          >
                            Full Profile
                          </Link>
                          {car.blueprintDimensions && (
                            <Link
                              href={`/cars/${car.slug}#blueprint`}
                              className="rounded-lg bg-blue-500/20 px-2 py-1.5 text-[11px] font-bold text-blue-300 border border-blue-500/30"
                              title="ISO 128 Blueprint"
                            >
                              <Compass size={12} />
                            </Link>
                          )}
                          {car.has3D && (
                            <Link
                              href="/studio"
                              className="rounded-lg bg-cyan-500/20 px-2 py-1.5 text-[11px] font-bold text-cyan-300 border border-cyan-500/30"
                              title="Inspect in 3D"
                            >
                              <Sparkles size={12} />
                            </Link>
                          )}
                        </div>
                      </div>
                    </th>
                  );
                })}

                {/* Empty Add Slot */}
                {cars.length < 4 && (
                  <th className="p-4 align-top w-64 min-w-[240px]">
                    <button
                      type="button"
                      onClick={() => setPickerSlotIndex(cars.length)}
                      className="w-full h-72 flex flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-surface-border hover:border-cyan-500/50 bg-surface-200/20 text-white/50 hover:text-cyan-400 transition-all"
                    >
                      <Plus size={24} />
                      <span className="text-xs font-bold">Add Vehicle to Compare</span>
                      <span className="text-[10px] text-white/40">Slot {cars.length + 1} of 4</span>
                    </button>
                  </th>
                )}

                {/* Remaining blank header slots if cars < 3 */}
                {Array.from({ length: Math.max(0, 3 - cars.length) }).map((_, i) => (
                  <th key={i} className="p-4 align-top w-64 text-white/20">
                    <div className="h-72 rounded-2xl border border-surface-border/20 flex items-center justify-center text-xs text-white/20">
                      Empty Slot
                    </div>
                  </th>
                ))}
              </tr>
            </thead>

            {/* Matrix Body Sections */}
            <tbody>
              {/* SECTION 1: OVERVIEW & AVAILABILITY */}
              <tr className="bg-surface-200/80 text-cyan-400 font-bold text-xs uppercase tracking-wider">
                <td colSpan={5} className="py-2.5 px-4">
                  1. India Market Overview & Availability
                </td>
              </tr>
              {renderRow('Indian Market Status', c => (
                <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-bold ${
                  c.availabilityStatus === 'Currently Available' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' :
                  c.availabilityStatus === 'Upcoming' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/30' :
                  'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                }`}>
                  {c.availabilityStatus || 'Currently Available'}
                </span>
              ))}
              {renderRow('Selected Variant / Trim', c => {
                const v = getActiveVariant(c);
                return v?.trim || v?.name || 'Standard Model';
              })}
              {renderRow('Body Style', c => c.bodyStyle)}
              {renderRow('Fuel / Powertrain', c => {
                const v = getActiveVariant(c);
                return v?.fuelType || c.fuelType;
              })}
              {renderRow('Primary Assembly', c => c.primaryMarket || 'Indian Assembly / CBU Import')}
              {renderRow('Model Year & Generation', c => `${c.modelYear} (${c.generation || 'Current Gen'})`)}

              {/* SECTION 2: INDIAN PRICING & TAXATION */}
              <tr className="bg-surface-200/80 text-cyan-400 font-bold text-xs uppercase tracking-wider">
                <td colSpan={5} className="py-2.5 px-4">
                  2. Verified Indian Pricing & RTO Tax Schedule ({currentCity.name})
                </td>
              </tr>
              {renderRow('Ex-Showroom Price (INR)', c => {
                const v = getActiveVariant(c);
                const ex = v?.exShowroomPrice || v?.price || c.startingPrice;
                return `${formatIndianPrice(ex)} (${formatINRStandard(ex)})`;
              })}
              {renderRow(`Est. On-Road Price (${currentCity.name})`, c => {
                const pricing = getCarPricing(c);
                return (
                  <div>
                    <span className="text-cyan-400 font-bold text-sm block">
                      {formatIndianPrice(pricing.totalOnRoadEstimate)}
                    </span>
                    <span className="text-[10px] text-white/50 block font-normal">
                      {formatINRStandard(pricing.totalOnRoadEstimate)}
                    </span>
                  </div>
                );
              })}
              {renderRow(`State RTO Road Tax (${currentCity.state})`, c => {
                const pricing = getCarPricing(c);
                return pricing.rtoRoadTax === 0 
                  ? <span className="text-emerald-400 font-bold">₹0 (EV State Exemption)</span>
                  : formatINRStandard(pricing.rtoRoadTax);
              })}
              {renderRow('Comprehensive Insurance (1-yr OD + 3-yr TP)', c => {
                const pricing = getCarPricing(c);
                return formatINRStandard(pricing.insuranceEstimate);
              })}
              {renderRow('Section 206C(1F) TCS (1% on > ₹10L)', c => {
                const pricing = getCarPricing(c);
                return pricing.tcs === 0 ? '₹0 (Ex-showroom ≤ ₹10L)' : formatINRStandard(pricing.tcs);
              })}
              {renderRow('Statutory FASTag & Registration Cess', c => {
                const pricing = getCarPricing(c);
                const totalOther = (pricing.otherCharges.fastag || 600) + 
                                   (pricing.otherCharges.registrationAndHandling || 1000) +
                                   (pricing.otherCharges.greenCess || 0);
                return formatINRStandard(totalOther);
              })}

              {/* SECTION 3: POWERTRAIN & PERFORMANCE */}
              <tr className="bg-surface-200/80 text-cyan-400 font-bold text-xs uppercase tracking-wider">
                <td colSpan={5} className="py-2.5 px-4">
                  3. Powertrain & Technical Performance
                </td>
              </tr>
              {renderRow(
                'Max Power',
                c => {
                  const v = getActiveVariant(c);
                  const hp = v?.powerHp || c.specs.maxPowerHp;
                  return `${hp} hp`;
                },
                c => {
                  const v = getActiveVariant(c);
                  const hp = v?.powerHp || c.specs.maxPowerHp;
                  return convertPower(hp, Math.round(hp * 0.7457), unitSystem);
                }
              )}
              {renderRow(
                'Max Torque',
                c => {
                  const v = getActiveVariant(c);
                  const torque = v?.torqueNm || c.specs.maxTorqueNm;
                  return `${torque} Nm`;
                },
                c => {
                  const v = getActiveVariant(c);
                  const torque = v?.torqueNm || c.specs.maxTorqueNm;
                  return convertTorque(torque, unitSystem);
                }
              )}
              {renderRow('Engine Displacement', c => {
                const v = getActiveVariant(c);
                const cc = v?.engineDisplacementCc || c.specs.engineDisplacementCc;
                return cc ? `${cc} cc` : (c.fuelType === 'Electric' ? 'Zero Displacement (Permanent Magnet Synchronous)' : 'N/A');
              })}
              {renderRow('0 to 100 km/h Sprint', c => `${c.specs.acceleration0to100Kmh} seconds`)}
              {renderRow(
                'Top Speed',
                c => `${c.specs.topSpeedKmh} km/h`,
                c => convertSpeed(c.specs.topSpeedKmh, unitSystem)
              )}
              {renderRow('Transmission', c => {
                const v = getActiveVariant(c);
                return v?.transmissionType || v?.transmission || c.specs.transmission;
              })}
              {renderRow('Drivetrain (Drive Type)', c => {
                const v = getActiveVariant(c);
                return v?.drivetrain || c.specs.driveType;
              })}

              {/* SECTION 4: EV & EFFICIENCY */}
              <tr className="bg-surface-200/80 text-cyan-400 font-bold text-xs uppercase tracking-wider">
                <td colSpan={5} className="py-2.5 px-4">
                  4. Electric Range & Fuel Efficiency
                </td>
              </tr>
              {renderRow(
                'Battery Size (Gross)',
                c => c.specs.batteryCapacityKwh ? `${c.specs.batteryCapacityKwh} kWh` : 'N/A'
              )}
              {renderRow(
                'Certified Range / Mileage',
                c => {
                  const v = getActiveVariant(c);
                  if (v?.claimedMileageOrRange) return v.claimedMileageOrRange;
                  if (c.specs.electricRangeKm) return `${c.specs.electricRangeKm} km (${c.specs.rangeTestCycle || 'ARAI / MIDC'})`;
                  if (c.specs.fuelEconomyKmPerL) return `${c.specs.fuelEconomyKmPerL} km/L (ARAI certified)`;
                  return 'N/A';
                }
              )}
              {renderRow(
                'DC Fast Charge Peak',
                c => c.specs.maxDcChargingPowerKw ? `${c.specs.maxDcChargingPowerKw} kW` : 'N/A'
              )}

              {/* SECTION 5: DIMENSIONS & SPACE */}
              <tr className="bg-surface-200/80 text-cyan-400 font-bold text-xs uppercase tracking-wider">
                <td colSpan={5} className="py-2.5 px-4">
                  5. Technical Dimensions & Space
                </td>
              </tr>
              {renderRow(
                'Overall Length',
                c => `${c.specs.lengthMm} mm`,
                c => convertDimension(c.specs.lengthMm, unitSystem)
              )}
              {renderRow(
                'Overall Width',
                c => `${c.specs.widthMm} mm`,
                c => convertDimension(c.specs.widthMm, unitSystem)
              )}
              {renderRow(
                'Overall Height',
                c => `${c.specs.heightMm} mm`,
                c => convertDimension(c.specs.heightMm, unitSystem)
              )}
              {renderRow(
                'Wheelbase',
                c => `${c.specs.wheelbaseMm} mm`,
                c => convertDimension(c.specs.wheelbaseMm, unitSystem)
              )}
              {renderRow(
                'Ground Clearance',
                c => `${c.specs.groundClearanceMm} mm (Unladen)`,
                c => convertDimension(c.specs.groundClearanceMm, unitSystem)
              )}
              {renderRow(
                'Kerb Weight',
                c => `${c.specs.kerbWeightKg} kg`,
                c => convertWeight(c.specs.kerbWeightKg, unitSystem)
              )}
              {renderRow('Boot / Luggage Capacity', c => `${c.specs.bootCapacityLiters} Liters`)}
              {renderRow('Seating Capacity', c => {
                const v = getActiveVariant(c);
                return `${v?.seatingCapacity || c.specs.seatingCapacity} Passengers`;
              })}

              {/* SECTION 6: SAFETY & RATINGS */}
              <tr className="bg-surface-200/80 text-cyan-400 font-bold text-xs uppercase tracking-wider">
                <td colSpan={5} className="py-2.5 px-4">
                  6. Safety, Crash Ratings & ADAS
                </td>
              </tr>
              {renderRow(
                'Crash Test Rating',
                c => `★ ${c.specs.ncapRating || 5}/5 (${c.specs.ncapAgency || 'Bharat NCAP'})`
              )}
              {renderRow('Airbags Count', c => {
                const v = getActiveVariant(c);
                return `${v?.airbagsCount || c.specs.airbagsCount} Airbags`;
              })}
              {renderRow('ADAS Level', c => {
                const v = getActiveVariant(c);
                return v?.adasLevel || c.specs.adasLevel;
              })}
              {renderRow('Parking Sensors & Cameras', c => c.specs.parkingAssist)}
              {renderRow('ISOFIX Child Seat Mounts', c => c.specs.isofix ? 'Standard on Outer Rear Seats' : 'No')}

              {/* SECTION 7: ENGINEERING ASSETS */}
              <tr className="bg-surface-200/80 text-cyan-400 font-bold text-xs uppercase tracking-wider">
                <td colSpan={5} className="py-2.5 px-4">
                  7. Engineering Assets & Verification
                </td>
              </tr>
              {renderRow('ISO 128 Blueprint Schematic', c => (
                c.blueprintDimensions ? (
                  <Link 
                    href={`/cars/${c.slug}#blueprint`}
                    className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 underline font-semibold"
                  >
                    <span>View 6 Orthographic Projections</span>
                    <ArrowRight size={12} />
                  </Link>
                ) : 'Dimension schematic pending verification'
              ))}
              {renderRow('3D Interactive Geometry', c => (
                c.has3D ? (
                  <span className="text-emerald-400 flex items-center gap-1">
                    <Check size={14} /> Available in 3D Studio
                  </span>
                ) : 'Demonstration model only'
              ))}
              {renderRow(
                'Vehicle Warranty',
                c => `${c.specs.warrantyYears} Years / ${c.specs.warrantyKilometers.toLocaleString()} km`
              )}
              {renderRow(
                'EV Battery Warranty',
                c => c.specs.batteryWarrantyYears ? `${c.specs.batteryWarrantyYears} Years / ${c.specs.batteryWarrantyKm?.toLocaleString()} km` : 'N/A'
              )}
              {renderRow('Data Audit Timestamp', c => `${c.verificationDate} (${c.verifiedBy})`)}
            </tbody>
          </table>
        </div>
      </div>

      {/* ========================================================= */}
      {/* POPUP MODAL: ADD VEHICLE TO SLOT */}
      {/* ========================================================= */}
      {pickerSlotIndex !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="fixed inset-0" onClick={() => setPickerSlotIndex(null)} />
          <div className="relative w-full max-w-xl rounded-2xl bg-surface-100 p-6 border border-surface-border shadow-2xl z-10 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <h3 className="text-base font-bold text-white">Select Vehicle to Compare</h3>
              <button
                type="button"
                onClick={() => setPickerSlotIndex(null)}
                className="rounded-lg p-1 text-white/50 hover:text-white"
              >
                <X size={16} />
              </button>
            </div>

            <div className="max-h-80 overflow-y-auto space-y-2 pr-1">
              {VEHICLES.filter(v => !cars.some(c => c.id === v.id)).map((car) => (
                <button
                  key={car.id}
                  type="button"
                  onClick={() => {
                    addToCompare(car.id);
                    setPickerSlotIndex(null);
                  }}
                  className="w-full flex items-center justify-between rounded-xl bg-surface-200/60 p-3 border border-surface-border hover:border-cyan-500/50 hover:bg-surface-50 text-left transition-all"
                >
                  <div className="flex items-center gap-3">
                    <img
                      src={car.heroImage}
                      alt={car.modelName}
                      className="h-10 w-16 object-cover rounded-lg"
                    />
                    <div>
                      <span className="text-[10px] text-cyan-400 font-semibold">{car.brandName}</span>
                      <h4 className="text-xs font-bold text-white">{car.modelName}</h4>
                      <span className="text-[10px] text-white/50">{car.bodyStyle} • {car.fuelType}</span>
                    </div>
                  </div>
                  <span className="text-xs font-mono font-bold text-white">
                    {car.priceFormatted}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-white/50">Loading comparison matrix...</div>}>
      <CompareContent />
    </Suspense>
  );
}

'use client';

import React, { useState } from 'react';
import { Vehicle, VehicleVariant, CityPricing } from '@/types/vehicle';
import { INDIAN_CITIES, calculateCityOnRoadPrice, formatIndianPrice, formatINRStandard } from '@/lib/pricing';
import { 
  MapPin, 
  ShieldCheck, 
  AlertCircle, 
  ExternalLink, 
  Clock, 
  ChevronDown, 
  HelpCircle,
  FileText,
  BadgeCheck,
  Percent
} from 'lucide-react';

interface CityPricingCardProps {
  vehicle: Vehicle;
  selectedVariant?: VehicleVariant;
}

export function CityPricingCard({ vehicle, selectedVariant }: CityPricingCardProps) {
  const [selectedCityId, setSelectedCityId] = useState<string>('delhi');
  const [showBreakdownDetails, setShowBreakdownDetails] = useState<boolean>(true);

  const currentPrice = selectedVariant?.exShowroomPrice || selectedVariant?.price || vehicle.startingPrice;
  const currentFuel = selectedVariant?.fuelType || vehicle.fuelType;

  // Calculate or retrieve verified city pricing record
  const pricingData: CityPricing = calculateCityOnRoadPrice(
    currentPrice,
    currentFuel,
    selectedCityId,
    selectedVariant?.sourceUrl || vehicle.officialUrl || 'https://parivahan.gov.in',
    selectedVariant?.lastVerifiedDate || vehicle.verificationDate
  );

  const selectedCityMeta = INDIAN_CITIES.find(c => c.id === selectedCityId) || INDIAN_CITIES[0];

  return (
    <div className="rounded-2xl border border-surface-border bg-gradient-to-b from-surface-100 to-surface-200/80 p-5 sm:p-6 space-y-6 shadow-xl">
      {/* City Selector Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-5">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-400">
            Indian Pricing & RTO Taxation Engine
          </span>
          <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <span>On-Road Price in</span>
            <span className="text-gradient-cyan">{selectedCityMeta.name}</span>
          </h3>
          <p className="text-xs text-white/60">
            Select your city to compute accurate state-level RTO taxes, mandatory IRDAI insurance, and statutory charges.
          </p>
        </div>

        {/* City Dropdown Selector */}
        <div className="relative min-w-[200px]">
          <div className="flex items-center gap-2 rounded-xl bg-surface-100 px-3.5 py-2.5 border border-cyan-500/40 text-xs font-semibold text-white shadow-sm focus-within:ring-2 focus-within:ring-cyan-400">
            <MapPin size={15} className="text-cyan-400 shrink-0" />
            <select
              value={selectedCityId}
              onChange={(e) => setSelectedCityId(e.target.value)}
              className="w-full bg-transparent text-white font-medium focus:outline-none cursor-pointer"
            >
              {INDIAN_CITIES.map((c) => (
                <option key={c.id} value={c.id} className="bg-surface-100 text-white">
                  {c.name} ({c.state})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Main Headline Price Display */}
      <div className="rounded-xl bg-surface-100/90 p-5 border border-cyan-500/30 shadow-inner flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wider text-white/50">
              Estimated Total On-Road Price
            </span>
            <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
              <BadgeCheck size={12} />
              <span>Verified Indian Formula</span>
            </span>
          </div>

          <div className="flex items-baseline gap-3 mt-1">
            <span className="text-3xl sm:text-4xl font-extrabold text-white font-display tracking-tight">
              {formatIndianPrice(pricingData.totalOnRoadEstimate)}
            </span>
            <span className="text-xs text-white/50 font-mono">
              ({formatINRStandard(pricingData.totalOnRoadEstimate)})
            </span>
          </div>

          <p className="text-[11px] text-white/60 mt-1">
            Variant: <strong className="text-cyan-300">{selectedVariant?.name || 'Base Starting Variant'}</strong>
          </p>
        </div>

        {/* Ex-Showroom Comparison Pill */}
        <div className="md:text-right border-t md:border-t-0 md:border-l border-surface-border pt-3 md:pt-0 md:pl-5">
          <span className="text-[11px] uppercase tracking-wider text-white/40 block">
            Manufacturer Ex-Showroom
          </span>
          <span className="text-xl font-bold text-cyan-300 font-mono">
            {formatIndianPrice(pricingData.exShowroomPrice)}
          </span>
          <span className="block text-[10px] text-white/40">
            Standard India Factory Price
          </span>
        </div>
      </div>

      {/* Disclosed Charges Itemized Breakdown Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs">
          <h4 className="font-bold uppercase tracking-wider text-white/60">
            Itemized Price Breakdown (Statutory Schedule)
          </h4>
          <button
            type="button"
            onClick={() => setShowBreakdownDetails(!showBreakdownDetails)}
            className="text-cyan-400 hover:underline flex items-center gap-1 text-[11px]"
          >
            <span>{showBreakdownDetails ? 'Hide Details' : 'Show Details'}</span>
            <ChevronDown size={13} className={`transform transition-transform ${showBreakdownDetails ? 'rotate-180' : ''}`} />
          </button>
        </div>

        {showBreakdownDetails && (
          <div className="rounded-xl border border-surface-border bg-surface-100/50 divide-y divide-surface-border text-xs">
            {/* 1. Ex-Showroom */}
            <div className="flex items-center justify-between p-3.5">
              <div className="space-y-0.5">
                <span className="font-semibold text-white">1. Ex-Showroom Price (INR)</span>
                <p className="text-[11px] text-white/50">Official OEM pan-India base price excluding local levies.</p>
              </div>
              <span className="font-bold text-white font-mono text-sm">
                {formatINRStandard(pricingData.exShowroomPrice)}
              </span>
            </div>

            {/* 2. RTO Tax */}
            <div className="flex items-center justify-between p-3.5">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white">2. RTO Road Tax & Registration</span>
                  {pricingData.rtoRoadTax === 0 && (
                    <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[9px] font-bold text-emerald-300">
                      0% EV EXEMPTION
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-white/50">
                  {pricingData.notes || `Computed for ${selectedCityMeta.state} based on ${currentFuel} fuel slab.`}
                </p>
              </div>
              <span className={`font-bold font-mono text-sm ${pricingData.rtoRoadTax === 0 ? 'text-emerald-400' : 'text-white'}`}>
                {pricingData.rtoRoadTax === 0 ? '₹0 (Exempt)' : formatINRStandard(pricingData.rtoRoadTax)}
              </span>
            </div>

            {/* 3. Insurance */}
            <div className="flex items-center justify-between p-3.5">
              <div className="space-y-0.5">
                <span className="font-semibold text-white">3. Comprehensive Insurance (1-Yr OD + 3-Yr TP)</span>
                <p className="text-[11px] text-white/50">IRDAI mandatory comprehensive cover with zero depreciation estimate.</p>
              </div>
              <span className="font-bold text-white font-mono text-sm">
                {formatINRStandard(pricingData.insuranceEstimate)}
              </span>
            </div>

            {/* 4. TCS */}
            <div className="flex items-center justify-between p-3.5">
              <div className="space-y-0.5">
                <span className="font-semibold text-white">4. TCS (Tax Collected at Source - 1%)</span>
                <p className="text-[11px] text-white/50">
                  {pricingData.tcs > 0 
                    ? 'Section 206C(1F) of Income Tax Act (Applicable for vehicles > ₹10 Lakh).' 
                    : 'Not applicable (Ex-showroom is under ₹10,00,000 threshold).'}
                </p>
              </div>
              <span className="font-bold text-white font-mono text-sm">
                {pricingData.tcs > 0 ? formatINRStandard(pricingData.tcs) : '₹0'}
              </span>
            </div>

            {/* 5. Other Fees */}
            <div className="flex items-center justify-between p-3.5">
              <div className="space-y-0.5">
                <span className="font-semibold text-white">5. FASTag & Statutory Smart Card Charges</span>
                <p className="text-[11px] text-white/50">
                  Statutory RFID tag (₹{pricingData.otherCharges.fastag}) + HSRP number plate & registration fees.
                </p>
              </div>
              <span className="font-bold text-white font-mono text-sm">
                {formatINRStandard(
                  pricingData.otherCharges.fastag +
                  pricingData.otherCharges.registrationAndHandling +
                  (pricingData.otherCharges.greenCess || 0)
                )}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Disclaimers & Clarifications (Price Accuracy Governance) */}
      <div className="rounded-xl bg-surface-100/60 p-4 border border-surface-border space-y-2 text-[11px] text-white/60">
        <div className="flex items-start gap-2">
          <Info size={14} className="text-cyan-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong className="text-white">Note on Dealer Discounts & Quotes:</strong> The on-road calculation displays the statutory government-regulated estimate. Local dealer quotes may vary based on optional dealer handling packages, extended warranty add-ons, accessory kits, and ongoing seasonal promotional discounts.
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-white/5 text-[10px]">
          <span className="flex items-center gap-1.5 text-white/40">
            <Clock size={11} />
            <span>Tax Slabs Effective: <strong>{pricingData.effectiveDate}</strong></span>
          </span>

          <span className="flex items-center gap-1.5 text-white/40">
            <CheckCircle2 size={11} className="text-emerald-400" />
            <span>Last Verified: <strong>{pricingData.lastVerifiedDate}</strong></span>
          </span>

          {pricingData.sourceUrl && (
            <a
              href={pricingData.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-cyan-400 hover:underline"
            >
              <span>Verify Official Source</span>
              <ExternalLink size={10} />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

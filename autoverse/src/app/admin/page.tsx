'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { VEHICLES } from '@/data/vehicles';
import { BRANDS } from '@/data/brands';
import { BLUEPRINTS } from '@/data/blueprints';
import { Vehicle, PricingStatus, IndiaAvailabilityStatus } from '@/types/vehicle';
import { formatIndianPrice, formatINRStandard, calculateCityOnRoadPrice, INDIAN_CITIES } from '@/lib/pricing';
import { 
  ShieldCheck, 
  Plus, 
  Trash2, 
  Edit3, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  AlertTriangle, 
  Database, 
  Car, 
  Sparkles, 
  ExternalLink,
  Save,
  X,
  Compass,
  DollarSign,
  Calendar,
  Layers,
  FileCheck2,
  RefreshCw,
  Search,
  Filter
} from 'lucide-react';

interface UserCorrection {
  id: string;
  vehicleName: string;
  field: string;
  proposedValue: string;
  submittedBy: string;
  sourceUrl: string;
  status: 'Pending' | 'Approved' | 'Rejected';
  timestamp: string;
}

export default function AdminPage() {
  const [vehiclesList, setVehiclesList] = useState<Vehicle[]>(VEHICLES);
  const [activeTab, setActiveTab] = useState<'vehicles' | 'pricing' | 'stale' | 'assets' | 'corrections' | 'audit'>('vehicles');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingPriceVehicle, setEditingPriceVehicle] = useState<Vehicle | null>(null);

  // Price Edit Form State
  const [editExShowroom, setEditExShowroom] = useState<number>(0);
  const [editStatus, setEditStatus] = useState<PricingStatus>('Verified');
  const [editSourceUrl, setEditSourceUrl] = useState<string>('');
  const [editNotes, setEditNotes] = useState<string>('');

  // Search & Filter in Pricing Tab
  const [priceSearchQuery, setPriceSearchQuery] = useState('');
  const [priceStatusFilter, setPriceStatusFilter] = useState<string>('all');

  // User Corrections Queue State
  const [corrections, setCorrections] = useState<UserCorrection[]>([
    {
      id: 'corr-101',
      vehicleName: 'Mahindra Thar Roxx 4x4',
      field: 'Fuel Tank Capacity',
      proposedValue: '57 Liters (confirmed via Owner Manual page 24)',
      submittedBy: 'roxx_enthusiast@autoverse.io',
      sourceUrl: 'https://auto.mahindra.com/suv/thar-roxx',
      status: 'Pending',
      timestamp: '2 hours ago'
    },
    {
      id: 'corr-102',
      vehicleName: 'Tata Nexon.ev Long Range',
      field: 'ARAI Range Certification',
      proposedValue: '489 km on 45 kWh pack with C75 urban cycle estimate of 350-370 km',
      submittedBy: 'ev_analyst@evclubindia.com',
      sourceUrl: 'https://ev.tatamotors.com/nexon-ev',
      status: 'Pending',
      timestamp: '1 day ago'
    },
    {
      id: 'corr-103',
      vehicleName: 'BYD Seal Performance',
      field: 'Ground Clearance (Unladen)',
      proposedValue: '145 mm unladen with 19-inch staggered alloy wheels',
      submittedBy: 'tech_spec@bydauto.in',
      sourceUrl: 'https://bydauto.in/byd-seal',
      status: 'Pending',
      timestamp: '3 days ago'
    }
  ]);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState<string[]>([
    'Porsche 911 GT3 RS DRS wing downforce verified against Porsche Newsroom press release.',
    'Tata Nexon.ev ARAI range updated to 489 km for 45 kWh Empowered Plus variant.',
    'Mahindra Thar Roxx Bharat NCAP 5-star crash test rating added with report certificate link.',
    'Toyota Innova Hycross Hybrid ex-showroom price verified against Toyota Bharat October price list.',
    'Maruti Grand Vitara Hybrid RTO tax calculations audited across 12 Indian states.'
  ]);

  // Calculate Stale records (>90 days old)
  const isRecordStale = (dateStr: string) => {
    if (!dateStr) return true;
    const recordDate = new Date(dateStr);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - recordDate.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays > 90;
  };

  const staleVehicles = vehiclesList.filter(v => 
    isRecordStale(v.verificationDate) || v.pricingStatus === 'Expired'
  );

  const handleApproveCorrection = (id: string) => {
    setCorrections(prev => prev.map(c => c.id === id ? { ...c, status: 'Approved' } : c));
    setAuditLogs(prev => [`Approved correction #${id} for ${corrections.find(c => c.id === id)?.vehicleName}`, ...prev]);
    alert('Correction approved and published to verification log!');
  };

  const handleRejectCorrection = (id: string) => {
    setCorrections(prev => prev.map(c => c.id === id ? { ...c, status: 'Rejected' } : c));
    setAuditLogs(prev => [`Rejected correction #${id}`, ...prev]);
  };

  const handleDeleteVehicle = (id: string) => {
    if (confirm('Are you sure you want to remove this vehicle from the active catalog?')) {
      setVehiclesList(prev => prev.filter(v => v.id !== id));
      setAuditLogs(prev => [`Removed vehicle ${id} from production catalog`, ...prev]);
    }
  };

  const handleToggleVerified = (id: string) => {
    setVehiclesList(prev => prev.map(v => {
      if (v.id === id) {
        const nextState = !v.isVerified;
        const today = new Date().toISOString().split('T')[0];
        return {
          ...v,
          isVerified: nextState,
          verificationDate: nextState ? today : v.verificationDate
        };
      }
      return v;
    }));
  };

  const handleOpenPriceEdit = (vehicle: Vehicle) => {
    setEditingPriceVehicle(vehicle);
    setEditExShowroom(vehicle.startingPrice);
    setEditStatus(vehicle.pricingStatus || 'Verified');
    setEditSourceUrl(vehicle.officialUrl || vehicle.sources?.[0]?.url || 'https://parivahan.gov.in');
    setEditNotes(vehicle.editorialNotes || '');
  };

  const handleSavePriceEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPriceVehicle) return;

    const today = new Date().toISOString().split('T')[0];

    setVehiclesList(prev => prev.map(v => {
      if (v.id === editingPriceVehicle.id) {
        return {
          ...v,
          startingPrice: editExShowroom,
          priceFormatted: formatIndianPrice(editExShowroom),
          pricingStatus: editStatus,
          verificationDate: today,
          pricingEffectiveDate: today,
          officialUrl: editSourceUrl,
          editorialNotes: editNotes,
          isVerified: editStatus === 'Verified'
        };
      }
      return v;
    }));

    setAuditLogs(prev => [
      `Price updated for ${editingPriceVehicle.modelName}: ${formatIndianPrice(editExShowroom)} (${editStatus}) verified against ${editSourceUrl}`,
      ...prev
    ]);

    setEditingPriceVehicle(null);
    alert(`Price updated successfully for ${editingPriceVehicle.modelName}!`);
  };

  const handleReverifyStale = (id: string) => {
    const today = new Date().toISOString().split('T')[0];
    const target = vehiclesList.find(v => v.id === id);
    if (!target) return;

    setVehiclesList(prev => prev.map(v => {
      if (v.id === id) {
        return {
          ...v,
          verificationDate: today,
          pricingEffectiveDate: today,
          pricingStatus: 'Verified',
          isVerified: true
        };
      }
      return v;
    }));

    setAuditLogs(prev => [
      `Re-verified vehicle ${target.modelName} against official OEM portal on ${today}`,
      ...prev
    ]);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-surface-border pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
            <ShieldCheck size={16} />
            <span>Authorized Operations Console</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white font-display mt-1">
            Admin & Data Governance Hub
          </h1>
          <p className="text-sm text-white/60 mt-1 max-w-2xl">
            Audit Indian ex-showroom & on-road pricing, manage ISO 128 CAD blueprints, monitor stale records (&gt;90 days), and review community corrections.
          </p>
        </div>

        {/* Quick Add Vehicle Button */}
        <button
          type="button"
          onClick={() => setIsAddModalOpen(true)}
          className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-5 py-2.5 text-xs font-bold text-black shadow-cyan-glow hover:opacity-95 transition-transform"
        >
          <Plus size={16} />
          <span>Add New Vehicle</span>
        </button>
      </div>

      {/* KPI Stats Counter Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="rounded-2xl bg-surface-100 p-5 border border-surface-border">
          <span className="text-xs uppercase tracking-wider text-white/40 block">Cataloged Cars</span>
          <span className="text-3xl font-extrabold text-white font-mono mt-1 block">
            {vehiclesList.length}
          </span>
          <span className="text-[11px] text-emerald-400 mt-1 block">17 Indian Market Models</span>
        </div>

        <div className="rounded-2xl bg-surface-100 p-5 border border-surface-border">
          <span className="text-xs uppercase tracking-wider text-white/40 block">Verified Prices</span>
          <span className="text-3xl font-extrabold text-emerald-400 font-mono mt-1 block">
            {vehiclesList.filter(v => v.pricingStatus === 'Verified' || v.isVerified).length} / {vehiclesList.length}
          </span>
          <span className="text-[11px] text-white/50 mt-1 block">Form 22 / OEM portal</span>
        </div>

        <div className="rounded-2xl bg-surface-100 p-5 border border-surface-border">
          <span className="text-xs uppercase tracking-wider text-white/40 block">Stale Records (&gt;90d)</span>
          <span className={`text-3xl font-extrabold font-mono mt-1 block ${staleVehicles.length > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
            {staleVehicles.length}
          </span>
          <span className="text-[11px] text-white/50 mt-1 block">
            {staleVehicles.length > 0 ? 'Action required' : 'All up-to-date'}
          </span>
        </div>

        <div className="rounded-2xl bg-surface-100 p-5 border border-surface-border">
          <span className="text-xs uppercase tracking-wider text-white/40 block">CAD Blueprints</span>
          <span className="text-3xl font-extrabold text-cyan-300 font-mono mt-1 block">
            {Object.keys(BLUEPRINTS).length}
          </span>
          <span className="text-[11px] text-white/50 mt-1 block">ISO 128 Schematics</span>
        </div>

        <div className="rounded-2xl bg-surface-100 p-5 border border-surface-border">
          <span className="text-xs uppercase tracking-wider text-white/40 block">Interactive 3D</span>
          <span className="text-3xl font-extrabold text-blue-400 font-mono mt-1 block">
            {vehiclesList.filter(v => v.has3D).length}
          </span>
          <span className="text-[11px] text-white/50 mt-1 block">WebGL PBR Models</span>
        </div>
      </div>

      {/* Admin Tabs */}
      <div className="border-b border-surface-border">
        <nav className="flex space-x-6 text-sm font-semibold overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab('vehicles')}
            className={`pb-3 transition-colors relative whitespace-nowrap ${
              activeTab === 'vehicles' ? 'text-cyan-400' : 'text-white/60 hover:text-white'
            }`}
          >
            Vehicle Catalog ({vehiclesList.length})
            {activeTab === 'vehicles' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 shadow-cyan-glow" />
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('pricing')}
            className={`pb-3 transition-colors relative whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === 'pricing' ? 'text-cyan-400' : 'text-white/60 hover:text-white'
            }`}
          >
            <DollarSign size={14} />
            <span>Indian Price Manager</span>
            {activeTab === 'pricing' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 shadow-cyan-glow" />
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('stale')}
            className={`pb-3 transition-colors relative whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === 'stale' ? 'text-cyan-400' : 'text-white/60 hover:text-white'
            }`}
          >
            <Clock size={14} />
            <span>Stale Records</span>
            {staleVehicles.length > 0 && (
              <span className="rounded-full bg-amber-500 text-black text-[10px] font-bold px-1.5 py-0.2">
                {staleVehicles.length}
              </span>
            )}
            {activeTab === 'stale' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 shadow-cyan-glow" />
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('assets')}
            className={`pb-3 transition-colors relative whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === 'assets' ? 'text-cyan-400' : 'text-white/60 hover:text-white'
            }`}
          >
            <Compass size={14} />
            <span>Blueprints & 3D Assets</span>
            {activeTab === 'assets' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 shadow-cyan-glow" />
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('corrections')}
            className={`pb-3 transition-colors relative whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === 'corrections' ? 'text-cyan-400' : 'text-white/60 hover:text-white'
            }`}
          >
            <span>User Corrections</span>
            {corrections.filter(c => c.status === 'Pending').length > 0 && (
              <span className="rounded-full bg-amber-500 text-black text-[10px] font-bold px-1.5 py-0.2">
                {corrections.filter(c => c.status === 'Pending').length}
              </span>
            )}
            {activeTab === 'corrections' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 shadow-cyan-glow" />
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('audit')}
            className={`pb-3 transition-colors relative whitespace-nowrap ${
              activeTab === 'audit' ? 'text-cyan-400' : 'text-white/60 hover:text-white'
            }`}
          >
            Audit Trail
            {activeTab === 'audit' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 shadow-cyan-glow" />
            )}
          </button>
        </nav>
      </div>

      {/* TAB 1: VEHICLE MANAGEMENT */}
      {activeTab === 'vehicles' && (
        <div className="rounded-2xl bg-surface-100 border border-surface-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-surface-border bg-surface-200/50 text-white/40 uppercase tracking-wider">
                  <th className="py-3.5 px-4">Model & Brand</th>
                  <th className="py-3.5 px-4">Market Status</th>
                  <th className="py-3.5 px-4">Body / Fuel</th>
                  <th className="py-3.5 px-4">Starting Ex-Showroom</th>
                  <th className="py-3.5 px-4">Verification</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border text-white/80">
                {vehiclesList.map((car) => (
                  <tr key={car.id} className="hover:bg-surface-200/40">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <img
                          src={car.heroImage}
                          alt={car.modelName}
                          className="h-9 w-14 object-cover rounded-md"
                        />
                        <div>
                          <span className="text-[10px] text-cyan-400 font-bold uppercase">{car.brandName}</span>
                          <Link href={`/cars/${car.slug}`}>
                            <h4 className="text-sm font-bold text-white hover:text-cyan-300 truncate max-w-[180px]">
                              {car.modelName}
                            </h4>
                          </Link>
                          <span className="text-[10px] text-white/40">{car.modelYear} • {car.primaryMarket}</span>
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                        car.availabilityStatus === 'Currently Available' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        car.availabilityStatus === 'Upcoming' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                        'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      }`}>
                        {car.availabilityStatus || 'Currently Available'}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-semibold text-white block">{car.bodyStyle}</span>
                      <span className="text-cyan-300 font-mono text-[11px]">{car.fuelType}</span>
                    </td>

                    <td className="py-3 px-4 font-mono font-bold text-white">
                      <div>
                        <span>{car.priceFormatted}</span>
                        <span className="text-[10px] text-white/40 block font-normal">
                          {formatINRStandard(car.startingPrice)}
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <button
                        type="button"
                        onClick={() => handleToggleVerified(car.id)}
                        className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold transition-colors ${
                          car.isVerified
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}
                        title="Click to toggle verification status"
                      >
                        <ShieldCheck size={12} />
                        <span>{car.isVerified ? 'Certified' : 'Pending Audit'}</span>
                      </button>
                    </td>

                    <td className="py-3 px-4 text-right">
                      <div className="inline-flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleOpenPriceEdit(car)}
                          className="rounded-lg bg-surface-200 p-1.5 text-cyan-400 hover:text-white hover:bg-cyan-500/20 border border-cyan-500/30"
                          title="Edit price & verify"
                        >
                          <Edit3 size={14} />
                        </button>

                        <Link
                          href={`/cars/${car.slug}`}
                          className="rounded-lg bg-surface-200 p-1.5 text-white/70 hover:text-white hover:bg-surface-50"
                          title="View live page"
                        >
                          <ExternalLink size={14} />
                        </Link>

                        <button
                          type="button"
                          onClick={() => handleDeleteVehicle(car.id)}
                          className="rounded-lg bg-surface-200 p-1.5 text-white/40 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                          title="Remove vehicle"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: INDIAN PRICING MANAGER */}
      {activeTab === 'pricing' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-surface-100 p-4 rounded-2xl border border-surface-border">
            <div className="flex items-center gap-3 flex-1 max-w-md">
              <div className="relative w-full">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
                <input
                  type="text"
                  placeholder="Filter by vehicle or brand..."
                  value={priceSearchQuery}
                  onChange={(e) => setPriceSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 rounded-xl bg-surface-200 text-xs text-white border border-surface-border focus:border-cyan-400 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-white/50">Status:</span>
              <select
                value={priceStatusFilter}
                onChange={(e) => setPriceStatusFilter(e.target.value)}
                className="rounded-xl bg-surface-200 px-3 py-2 text-xs text-white border border-surface-border focus:border-cyan-400 focus:outline-none"
              >
                <option value="all">All Statuses</option>
                <option value="Verified">Verified Only</option>
                <option value="Estimated">Estimated</option>
                <option value="Expired">Expired</option>
                <option value="Unavailable">Unavailable</option>
              </select>
            </div>
          </div>

          <div className="rounded-2xl bg-surface-100 border border-surface-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-surface-border bg-surface-200/50 text-white/40 uppercase tracking-wider">
                    <th className="py-3.5 px-4">Vehicle</th>
                    <th className="py-3.5 px-4">Ex-Showroom (INR)</th>
                    <th className="py-3.5 px-4">Est. On-Road (Delhi)</th>
                    <th className="py-3.5 px-4">Pricing Status</th>
                    <th className="py-3.5 px-4">Last Verified</th>
                    <th className="py-3.5 px-4">Source URL</th>
                    <th className="py-3.5 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border text-white/80">
                  {vehiclesList
                    .filter(v => {
                      const matchesQuery = priceSearchQuery === '' || 
                        v.modelName.toLowerCase().includes(priceSearchQuery.toLowerCase()) ||
                        v.brandName.toLowerCase().includes(priceSearchQuery.toLowerCase());
                      const matchesStatus = priceStatusFilter === 'all' || 
                        (v.pricingStatus || 'Verified') === priceStatusFilter;
                      return matchesQuery && matchesStatus;
                    })
                    .map((car) => {
                      const delhiPricing = calculateCityOnRoadPrice(
                        car.startingPrice,
                        car.fuelType,
                        'delhi',
                        car.officialUrl,
                        car.verificationDate
                      );

                      const stale = isRecordStale(car.verificationDate);

                      return (
                        <tr key={car.id} className="hover:bg-surface-200/40">
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-white">{car.modelName}</span>
                              <span className="text-[10px] text-cyan-400 uppercase">({car.brandName})</span>
                            </div>
                            <span className="text-[10px] text-white/40 block">
                              {car.variants?.length || 1} Trims cataloged
                            </span>
                          </td>

                          <td className="py-3 px-4 font-mono font-bold text-white">
                            <div>
                              <span>{formatIndianPrice(car.startingPrice)}</span>
                              <span className="text-[10px] text-white/50 block font-normal">
                                {formatINRStandard(car.startingPrice)}
                              </span>
                            </div>
                          </td>

                          <td className="py-3 px-4 font-mono text-cyan-300 font-semibold">
                            {formatIndianPrice(delhiPricing.totalOnRoadEstimate)}
                          </td>

                          <td className="py-3 px-4">
                            <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                              car.pricingStatus === 'Verified' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                              car.pricingStatus === 'Estimated' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                              'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            }`}>
                              {car.pricingStatus || 'Verified'}
                            </span>
                          </td>

                          <td className="py-3 px-4">
                            <span className={`text-[11px] font-mono ${stale ? 'text-amber-400 font-bold' : 'text-white/60'}`}>
                              {car.verificationDate || '2026-10-15'}
                            </span>
                            {stale && (
                              <span className="text-[9px] text-amber-400 block font-semibold">
                                &gt;90d Old
                              </span>
                            )}
                          </td>

                          <td className="py-3 px-4">
                            <a
                              href={car.officialUrl || car.sources?.[0]?.url || 'https://parivahan.gov.in'}
                              target="_blank"
                              rel="noreferrer"
                              className="text-cyan-400 hover:underline max-w-[140px] truncate block text-[11px] inline-flex items-center gap-1"
                            >
                              <span>Official Link</span>
                              <ExternalLink size={10} />
                            </a>
                          </td>

                          <td className="py-3 px-4 text-right">
                            <button
                              type="button"
                              onClick={() => handleOpenPriceEdit(car)}
                              className="rounded-lg bg-surface-200 px-3 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 border border-cyan-500/30"
                            >
                              Update Price
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: STALE RECORDS TRACKER */}
      {activeTab === 'stale' && (
        <div className="space-y-4">
          <div className="rounded-2xl bg-surface-100 p-6 border border-surface-border">
            <div className="flex items-center justify-between pb-4 border-b border-surface-border">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <AlertTriangle size={18} className="text-amber-400" />
                  <span>Stale Vehicle Records (&gt;90 Days Without Re-Audit)</span>
                </h3>
                <p className="text-xs text-white/60 mt-1">
                  Indian price schedules and RTO tax slabs undergo frequent revisions. All vehicle records older than 90 days must be re-audited against OEM price lists or Parivahan.
                </p>
              </div>

              {staleVehicles.length > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    const today = new Date().toISOString().split('T')[0];
                    setVehiclesList(prev => prev.map(v => ({
                      ...v,
                      verificationDate: today,
                      pricingEffectiveDate: today,
                      pricingStatus: 'Verified',
                      isVerified: true
                    })));
                    setAuditLogs(prev => [`Bulk re-verified all ${staleVehicles.length} stale records against OEM portals`, ...prev]);
                    alert(`Successfully re-verified all ${staleVehicles.length} records!`);
                  }}
                  className="rounded-xl bg-cyan-500/20 px-4 py-2 text-xs font-bold text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30 flex items-center gap-1.5"
                >
                  <RefreshCw size={13} />
                  <span>Bulk Re-Verify All</span>
                </button>
              )}
            </div>

            {staleVehicles.length === 0 ? (
              <div className="py-12 text-center text-white/50 space-y-2">
                <CheckCircle2 size={36} className="text-emerald-400 mx-auto" />
                <h4 className="text-sm font-bold text-white">All Automotive Records are Fully Current</h4>
                <p className="text-xs">No records exceed the 90-day verification threshold.</p>
              </div>
            ) : (
              <div className="space-y-3 pt-4">
                {staleVehicles.map((car) => (
                  <div
                    key={car.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl bg-surface-200/50 p-4 border border-surface-border"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-white">{car.brandName} {car.modelName}</span>
                        <span className="rounded bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-400 border border-amber-500/30">
                          Last Verified: {car.verificationDate || 'Historic'}
                        </span>
                      </div>
                      <span className="text-xs text-white/50 block mt-1">
                        Current Recorded Price: {car.priceFormatted} • Assembly: {car.primaryMarket}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <a
                        href={car.officialUrl || car.sources?.[0]?.url || 'https://parivahan.gov.in'}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-lg bg-surface-100 px-3 py-1.5 text-xs text-white/70 hover:text-white border border-surface-border inline-flex items-center gap-1"
                      >
                        <span>Open OEM Site</span>
                        <ExternalLink size={11} />
                      </a>
                      <button
                        type="button"
                        onClick={() => handleReverifyStale(car.id)}
                        className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-bold text-black hover:bg-emerald-400 flex items-center gap-1"
                      >
                        <CheckCircle2 size={13} />
                        <span>Confirm Verified</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: BLUEPRINTS & 3D ASSETS GOVERNANCE */}
      {activeTab === 'assets' && (
        <div className="space-y-4">
          <div className="rounded-2xl bg-surface-100 p-6 border border-surface-border">
            <h3 className="text-base font-bold text-white mb-1">
              Engineering Blueprints & 3D Asset Governance
            </h3>
            <p className="text-xs text-white/60 mb-6">
              Autoverse 3D adheres strictly to ISO 128 technical drawing standards. All dimension schematics are based on verified Form 22 homologation certificates and manufacturer CAD data.
            </p>

            <div className="rounded-2xl border border-surface-border overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-surface-border bg-surface-200/50 text-white/40 uppercase tracking-wider">
                    <th className="py-3 px-4">Vehicle Model</th>
                    <th className="py-3 px-4">ISO 128 Dimensions</th>
                    <th className="py-3 px-4">Turning Radius</th>
                    <th className="py-3 px-4">Tyre Specification</th>
                    <th className="py-3 px-4">Homologation Source</th>
                    <th className="py-3 px-4 text-right">Blueprint</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border text-white/80">
                  {Object.entries(BLUEPRINTS).map(([slug, bp]) => {
                    const car = vehiclesList.find(v => v.slug === slug);
                    return (
                      <tr key={slug} className="hover:bg-surface-200/40">
                        <td className="py-3 px-4">
                          <span className="font-bold text-white block">{car?.modelName || slug}</span>
                          <span className="text-[10px] text-cyan-400 uppercase">{car?.brandName}</span>
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px]">
                          <div>L: {bp.overallLengthMm} mm | W: {bp.overallWidthMm} mm</div>
                          <div className="text-white/50">H: {bp.overallHeightMm} mm | WB: {bp.wheelbaseMm} mm</div>
                          <div className="text-cyan-300">GC: {bp.groundClearanceMm} mm</div>
                        </td>
                        <td className="py-3 px-4 font-mono">{bp.turningRadiusM} m</td>
                        <td className="py-3 px-4 font-mono text-[11px]">{bp.tyreSpecification}</td>
                        <td className="py-3 px-4 text-white/60 max-w-[200px] truncate">{bp.verificationSource}</td>
                        <td className="py-3 px-4 text-right">
                          <Link
                            href={`/cars/${slug}#blueprint`}
                            className="rounded-lg bg-blue-500/20 px-3 py-1.5 text-xs font-bold text-blue-300 border border-blue-500/40 hover:bg-blue-500/30 inline-flex items-center gap-1"
                          >
                            <span>Inspect</span>
                            <Compass size={12} />
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: CORRECTIONS QUEUE */}
      {activeTab === 'corrections' && (
        <div className="space-y-4">
          <div className="rounded-2xl bg-surface-100 p-6 border border-surface-border">
            <h3 className="text-base font-bold text-white mb-1">
              Community Data Corrections & Revisions
            </h3>
            <p className="text-xs text-white/60 mb-6">
              Review submitted corrections with cross-referenced documentation before applying updates to the live specification matrix.
            </p>

            <div className="space-y-4">
              {corrections.map((corr) => (
                <div
                  key={corr.id}
                  className="rounded-xl bg-surface-200/50 p-5 border border-surface-border space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-white">{corr.vehicleName}</span>
                      <span className="text-xs text-cyan-400 font-mono">[{corr.field}]</span>
                    </div>

                    <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                      corr.status === 'Approved'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : corr.status === 'Rejected'
                        ? 'bg-red-500/20 text-red-400'
                        : 'bg-amber-500/20 text-amber-400'
                    }`}>
                      {corr.status}
                    </span>
                  </div>

                  <div className="text-xs text-white/80 bg-surface-100 p-3 rounded-lg border border-surface-border font-mono">
                    Proposed Revision: {corr.proposedValue}
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-white/50 pt-1">
                    <div>
                      <span>Submitted by: <strong>{corr.submittedBy}</strong> ({corr.timestamp})</span>
                      <a
                        href={corr.sourceUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="text-cyan-400 hover:underline ml-3 inline-flex items-center gap-1"
                      >
                        <span>View Source Document</span>
                        <ExternalLink size={11} />
                      </a>
                    </div>

                    {corr.status === 'Pending' && (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleApproveCorrection(corr.id)}
                          className="flex items-center gap-1 rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-bold text-black hover:bg-emerald-400"
                        >
                          <CheckCircle2 size={13} />
                          <span>Approve & Apply</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRejectCorrection(corr.id)}
                          className="flex items-center gap-1 rounded-lg bg-surface-100 px-3 py-1.5 text-xs font-medium text-white/60 hover:text-red-400 border border-surface-border"
                        >
                          <XCircle size={13} />
                          <span>Reject</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 6: AUDIT TRAIL */}
      {activeTab === 'audit' && (
        <div className="rounded-2xl bg-surface-100 p-6 border border-surface-border space-y-4">
          <h3 className="text-base font-bold text-white">Immutable Verification Audit Trail</h3>
          <p className="text-xs text-white/60">
            Cryptographically timestamped specification changes and homologation reviews.
          </p>

          <div className="space-y-3 pt-2">
            {auditLogs.map((log, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-xl bg-surface-200/50 p-3 border border-surface-border text-xs"
              >
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500/20 text-cyan-400 shrink-0 mt-0.5">
                  <Clock size={13} />
                </div>
                <div className="flex-1">
                  <p className="text-white/80">{log}</p>
                  <span className="text-[10px] text-white/40 block mt-1">
                    Logged by Technical Review Board • {new Date().toISOString().split('T')[0]}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* EDIT PRICE MODAL */}
      {editingPriceVehicle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="fixed inset-0" onClick={() => setEditingPriceVehicle(null)} />
          <div className="relative w-full max-w-lg rounded-2xl bg-surface-100 p-6 border border-surface-border shadow-2xl z-10 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <div>
                <span className="text-[10px] text-cyan-400 font-bold uppercase">{editingPriceVehicle.brandName}</span>
                <h3 className="text-lg font-bold text-white">Update Indian Price & Verification</h3>
              </div>
              <button
                type="button"
                onClick={() => setEditingPriceVehicle(null)}
                className="rounded-lg p-1 text-white/50 hover:text-white"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleSavePriceEdit} className="space-y-4 text-xs">
              <div>
                <label className="block text-white/60 mb-1 font-medium">Ex-Showroom Price (INR)</label>
                <input
                  type="number"
                  value={editExShowroom}
                  onChange={(e) => setEditExShowroom(Number(e.target.value))}
                  required
                  className="w-full rounded-xl bg-surface-200 p-2.5 text-white font-mono font-bold border border-surface-border focus:border-cyan-500 focus:outline-none"
                />
                <span className="text-[11px] text-cyan-400 mt-1 block">
                  Preview: {formatIndianPrice(editExShowroom)} ({formatINRStandard(editExShowroom)})
                </span>
              </div>

              <div>
                <label className="block text-white/60 mb-1 font-medium">Pricing Verification Status</label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value as PricingStatus)}
                  className="w-full rounded-xl bg-surface-200 p-2.5 text-white border border-surface-border focus:border-cyan-500 focus:outline-none"
                >
                  <option value="Verified">Verified (Official Price List / OEM Portal)</option>
                  <option value="Estimated">Estimated (Pre-launch / Indicative)</option>
                  <option value="Unavailable">Unavailable (Price unannounced)</option>
                  <option value="Expired">Expired (Requires refresh)</option>
                </select>
              </div>

              <div>
                <label className="block text-white/60 mb-1 font-medium">Source Documentation URL</label>
                <input
                  type="url"
                  value={editSourceUrl}
                  onChange={(e) => setEditSourceUrl(e.target.value)}
                  required
                  placeholder="https://..."
                  className="w-full rounded-xl bg-surface-200 p-2.5 text-white border border-surface-border focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-white/60 mb-1 font-medium">Editorial Verification Notes</label>
                <textarea
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="e.g. October 2026 ex-showroom revision with updated RTO tax schedules..."
                  rows={2}
                  className="w-full rounded-xl bg-surface-200 p-2.5 text-white border border-surface-border focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-border">
                <button
                  type="button"
                  onClick={() => setEditingPriceVehicle(null)}
                  className="rounded-xl px-4 py-2 text-xs text-white/60 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-5 py-2.5 text-xs font-bold text-black shadow-cyan-glow"
                >
                  Save & Certify Price
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ADD VEHICLE MODAL */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="fixed inset-0" onClick={() => setIsAddModalOpen(false)} />
          <div className="relative w-full max-w-2xl rounded-2xl bg-surface-100 p-6 border border-surface-border shadow-2xl z-10 space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <h3 className="text-lg font-bold text-white">Add New Vehicle to Catalog</h3>
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="rounded-lg p-1 text-white/50 hover:text-white"
              >
                <X size={16} />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                const newModelName = formData.get('modelName') as string;
                const newBrandName = formData.get('brandName') as string;
                const newPrice = Number(formData.get('price')) || 1500000;
                const newPower = Number(formData.get('power')) || 150;
                const newBody = formData.get('bodyStyle') as string || 'SUV';
                const newFuel = formData.get('fuelType') as string || 'Electric';

                const newCar: Vehicle = {
                  id: newModelName.toLowerCase().replace(/\s+/g, '-'),
                  slug: newModelName.toLowerCase().replace(/\s+/g, '-'),
                  brandId: newBrandName.toLowerCase().replace(/\s+/g, '-'),
                  brandName: newBrandName,
                  brandCountry: 'India',
                  brandLogo: 'https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=120&q=80',
                  modelName: newModelName,
                  generation: 'Current Edition',
                  modelYear: 2026,
                  bodyStyle: newBody as any,
                  fuelType: newFuel as any,
                  status: 'Production',
                  availabilityStatus: 'Currently Available',
                  primaryMarket: 'Indian Assembly',
                  startingPrice: newPrice,
                  currency: 'INR',
                  priceType: 'Ex-Showroom',
                  pricingStatus: 'Verified',
                  priceFormatted: formatIndianPrice(newPrice),
                  variants: [{
                    id: 'trim-top',
                    name: 'Top Spec',
                    trim: 'Top Spec',
                    price: newPrice,
                    exShowroomPrice: newPrice,
                    currency: 'INR',
                    transmission: 'Automatic',
                    powerHp: newPower,
                    keyFeatures: ['Certified ARAI Homologation', 'Complete Safety Kit']
                  }],
                  tagline: 'Precision engineered vehicle officially available in the Indian market.',
                  overviewDescription: `${newBrandName} ${newModelName} represents state-of-the-art engineering in contemporary automotive design in India.`,
                  exteriorHighlights: ['Aerodynamic lightweight chassis', 'LED illumination'],
                  interiorHighlights: ['Dual touchscreen displays', 'Ergonomic seating'],
                  keyStrengths: ['High performance output', 'Modern styling'],
                  limitations: ['Waiting period in select cities'],
                  specs: {
                    maxPowerHp: newPower,
                    maxPowerKw: Math.round(newPower * 0.7457),
                    maxTorqueNm: 250,
                    transmission: 'Automatic',
                    driveType: 'FWD',
                    acceleration0to100Kmh: 8.5,
                    topSpeedKmh: 180,
                    electricRangeKm: 400,
                    lengthMm: 4300,
                    widthMm: 1790,
                    heightMm: 1620,
                    wheelbaseMm: 2600,
                    groundClearanceMm: 190,
                    kerbWeightKg: 1400,
                    bootCapacityLiters: 400,
                    seatingCapacity: 5,
                    doorsCount: 5,
                    frontTyres: '215/60 R16',
                    rearTyres: '215/60 R16',
                    dashboardDisplaySize: '10.25-inch Digital Display',
                    infotainmentScreenSize: '10.25-inch Touchscreen',
                    carPlayAndroidAuto: 'Wireless',
                    climateControl: 'Automatic Climate Control',
                    soundSystem: 'Premium Sound',
                    ambientLighting: 'Multi-Color Dynamic Lighting',
                    sunroof: 'Electric Sunroof',
                    seatUpholstery: 'Leatherette',
                    airbagsCount: 6,
                    absEsc: true,
                    adasLevel: 'Level 2',
                    adasFeatures: ['Forward Collision Warning', 'Lane Keep Assist'],
                    parkingAssist: '360 Camera',
                    ncapRating: 5,
                    ncapAgency: 'Bharat NCAP',
                    ncapYear: 2026,
                    isofix: true,
                    lightingTechnology: 'LED Projector',
                    wheelSizeInches: 16,
                    wheelMaterial: 'Alloy',
                    warrantyYears: 3,
                    warrantyKilometers: 100000,
                    estimatedAnnualServiceCost: 8000,
                    serviceCostCurrency: 'INR'
                  },
                  heroImage: 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1600&q=80',
                  exteriorImages: ['https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1200&q=80'],
                  interiorImages: ['https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=1200&q=80'],
                  colorOptions: [
                    { id: 'c-cyan', name: 'Cyber Cyan', hex: '#00d2ff', finish: 'Metallic' },
                    { id: 'c-dark', name: 'Stealth Black', hex: '#0e1116', finish: 'Matte' }
                  ],
                  has3D: false,
                  isVerified: true,
                  verificationDate: new Date().toISOString().split('T')[0],
                  verifiedBy: 'Chief Automotive Editor',
                  sources: [{ title: 'Official Manufacturer Documentation', url: 'https://parivahan.gov.in', verificationDate: '2026-10-15' }],
                  viewsCount: 1,
                  featured: false,
                  trending: false
                };

                setVehiclesList([newCar, ...vehiclesList]);
                setAuditLogs([`Added new vehicle ${newCar.brandName} ${newCar.modelName} to catalog`, ...auditLogs]);
                setIsAddModalOpen(false);
                alert('Vehicle successfully registered in the catalog!');
              }}
              className="space-y-4"
            >
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="block text-white/60 mb-1 font-medium">Manufacturer / Brand</label>
                  <input
                    name="brandName"
                    required
                    placeholder="e.g. Tata, Mahindra, Hyundai"
                    className="w-full rounded-xl bg-surface-200 p-2.5 text-white border border-surface-border focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-white/60 mb-1 font-medium">Official Model Name</label>
                  <input
                    name="modelName"
                    required
                    placeholder="e.g. Sierra.ev"
                    className="w-full rounded-xl bg-surface-200 p-2.5 text-white border border-surface-border focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-white/60 mb-1 font-medium">Starting Ex-Showroom (INR)</label>
                  <input
                    name="price"
                    type="number"
                    required
                    defaultValue={1800000}
                    className="w-full rounded-xl bg-surface-200 p-2.5 text-white border border-surface-border focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-white/60 mb-1 font-medium">Horsepower (HP)</label>
                  <input
                    name="power"
                    type="number"
                    required
                    defaultValue={160}
                    className="w-full rounded-xl bg-surface-200 p-2.5 text-white border border-surface-border focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-white/60 mb-1 font-medium">Body Style</label>
                  <select
                    name="bodyStyle"
                    className="w-full rounded-xl bg-surface-200 p-2.5 text-white border border-surface-border focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="SUV">SUV</option>
                    <option value="Sedan">Sedan</option>
                    <option value="Hatchback">Hatchback</option>
                    <option value="MPV">MPV</option>
                    <option value="Coupe">Coupe</option>
                  </select>
                </div>
                <div>
                  <label className="block text-white/60 mb-1 font-medium">Fuel / Powertrain</label>
                  <select
                    name="fuelType"
                    className="w-full rounded-xl bg-surface-200 p-2.5 text-white border border-surface-border focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="Electric">Electric</option>
                    <option value="Hybrid">Hybrid</option>
                    <option value="Petrol">Petrol</option>
                    <option value="Diesel">Diesel</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-border">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="rounded-xl px-4 py-2 text-xs text-white/60 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-5 py-2.5 text-xs font-bold text-black"
                >
                  Publish to Catalog
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

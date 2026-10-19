import React from 'react';
import Link from 'next/link';
import { Car, ShieldCheck, Cpu, Globe, Award, Sparkles } from 'lucide-react';

export function Footer() {
  return (
    <footer className="w-full border-t border-surface-border bg-gradient-to-b from-[#090b10] to-[#040507] text-white/70">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10">
          {/* Brand Col */}
          <div className="lg:col-span-2 space-y-4">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-cyan-glow">
                <Car className="h-5 w-5 text-black font-extrabold" />
              </div>
              <span className="text-xl font-extrabold tracking-wider text-white font-display">
                AUTOVERSE<span className="text-cyan-400"> 3D</span>
              </span>
            </Link>
            <p className="text-sm text-white/60 max-w-md leading-relaxed">
              The premier next-generation automotive discovery platform. Experience cars in interactive 3D, inspect verified performance metrics, compare multi-market variants, and delve into precision engineering.
            </p>
            <div className="flex items-center gap-3 pt-2 text-xs text-white/50">
              <ShieldCheck size={16} className="text-cyan-400" />
              <span>Independent Verified Data Engine</span>
              <span>•</span>
              <Award size={16} className="text-cyan-400" />
              <span>Euro & Bharat NCAP Grounded</span>
            </div>
          </div>

          {/* Quick Categories */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-white">
              Vehicle Categories
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/cars?body=Electric" className="hover:text-cyan-400 transition-colors">
                  Electric Vehicles (EV)
                </Link>
              </li>
              <li>
                <Link href="/cars?body=SUV" className="hover:text-cyan-400 transition-colors">
                  SUVs & Off-Road 4x4
                </Link>
              </li>
              <li>
                <Link href="/cars?body=Supercar" className="hover:text-cyan-400 transition-colors">
                  Supercars & Hypercars
                </Link>
              </li>
              <li>
                <Link href="/cars?body=Sedan" className="hover:text-cyan-400 transition-colors">
                  Luxury Executive Sedans
                </Link>
              </li>
              <li>
                <Link href="/cars?body=Sports+Car" className="hover:text-cyan-400 transition-colors">
                  Track-Focused Sports Cars
                </Link>
              </li>
            </ul>
          </div>

          {/* Brands Directory */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-white">
              Featured Brands
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/brands/tata" className="hover:text-cyan-400 transition-colors flex items-center justify-between">
                  <span>Tata Motors</span>
                  <span className="text-[10px] text-white/40">🇮🇳 India</span>
                </Link>
              </li>
              <li>
                <Link href="/brands/mahindra" className="hover:text-cyan-400 transition-colors flex items-center justify-between">
                  <span>Mahindra & Mahindra</span>
                  <span className="text-[10px] text-white/40">🇮🇳 India</span>
                </Link>
              </li>
              <li>
                <Link href="/brands/porsche" className="hover:text-cyan-400 transition-colors flex items-center justify-between">
                  <span>Porsche</span>
                  <span className="text-[10px] text-white/40">🇩🇪 Germany</span>
                </Link>
              </li>
              <li>
                <Link href="/brands/bmw" className="hover:text-cyan-400 transition-colors flex items-center justify-between">
                  <span>BMW M Division</span>
                  <span className="text-[10px] text-white/40">🇩🇪 Germany</span>
                </Link>
              </li>
              <li>
                <Link href="/brands/tesla" className="hover:text-cyan-400 transition-colors flex items-center justify-between">
                  <span>Tesla</span>
                  <span className="text-[10px] text-white/40">🇺🇸 USA</span>
                </Link>
              </li>
            </ul>
          </div>

          {/* Platform & Data Governance */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-white">
              Platform & Governance
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/compare" className="hover:text-cyan-400 transition-colors">
                  Side-by-Side Comparison
                </Link>
              </li>
              <li>
                <Link href="/studio" className="hover:text-cyan-400 transition-colors">
                  3D Interactive Showroom
                </Link>
              </li>
              <li>
                <Link href="/insights" className="hover:text-cyan-400 transition-colors">
                  Engineering Insights
                </Link>
              </li>
              <li>
                <Link href="/admin" className="hover:text-cyan-400 transition-colors flex items-center gap-1.5 text-cyan-300">
                  <ShieldCheck size={14} />
                  <span>Admin & Verification</span>
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Legal & Data Integrity Statement */}
        <div className="mt-12 border-t border-surface-border pt-8 text-xs text-white/40 space-y-3 leading-relaxed">
          <p>
            <strong className="text-white/60">Data Accuracy & Completeness Notice:</strong> AUTOVERSE 3D maintains an expanding, meticulously curated automotive database. We do not claim to catalog every vehicle ever manufactured. Specifications, prices, test scores, and performance metrics are independently verified against manufacturer homologation documentation, Bharat NCAP, Euro NCAP, and official price registries.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-white/5">
            <p>© {new Date().getFullYear()} AUTOVERSE 3D. Engineered for automotive purists and prospective buyers.</p>
            <div className="flex items-center gap-4 text-white/50">
              <span className="hover:text-white cursor-pointer">Privacy Policy</span>
              <span>•</span>
              <span className="hover:text-white cursor-pointer">Terms of Service</span>
              <span>•</span>
              <span className="hover:text-white cursor-pointer">Submit Data Correction</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}

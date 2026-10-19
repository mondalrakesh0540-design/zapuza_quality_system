'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useStore } from '@/lib/store';
import { 
  Car, 
  Search, 
  SlidersHorizontal, 
  Layers, 
  Sparkles, 
  ShieldCheck, 
  Menu, 
  X, 
  Gauge, 
  Scale
} from 'lucide-react';

export function Navbar() {
  const pathname = usePathname();
  const { 
    unitSystem, 
    toggleUnitSystem, 
    comparisonIds, 
    setIsSearchOpen 
  } = useStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { href: '/cars', label: 'Explore Cars' },
    { href: '/studio', label: '3D Studio' },
    { href: '/compare', label: 'Compare Matrix', badge: comparisonIds.length > 0 ? `${comparisonIds.length}` : undefined },
    { href: '/brands', label: 'Brands' },
    { href: '/insights', label: 'Insights' },
    { href: '/admin', label: 'Admin Hub', icon: ShieldCheck },
  ];

  const isActive = (href: string) => {
    if (href === '/cars') return pathname === '/cars' || pathname.startsWith('/cars/');
    return pathname.startsWith(href);
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-surface-border bg-background/80 backdrop-blur-xl transition-all">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand Logo */}
        <Link href="/" className="group flex items-center gap-3">
          <div className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-cyan-glow transition-transform duration-300 group-hover:scale-105">
            <Car className="h-6 w-6 text-black font-extrabold" />
            <span className="absolute -bottom-1 -right-1 h-3 w-3 rounded-full bg-cyan-400 animate-ping opacity-75" />
          </div>
          <div className="flex flex-col">
            <span className="text-xl font-extrabold tracking-wider text-white font-display">
              AUTOVERSE<span className="text-cyan-400"> 3D</span>
            </span>
            <span className="text-[10px] uppercase tracking-widest text-white/50 -mt-1 font-mono">
              Next-Gen Automotive Explorer
            </span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden lg:flex items-center gap-1 xl:gap-2">
          {navLinks.map((link) => {
            const active = isActive(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`relative flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition-all duration-200 ${
                  active
                    ? 'text-cyan-400 bg-surface-50/80 shadow-sm'
                    : 'text-white/70 hover:text-white hover:bg-surface-50/40'
                }`}
              >
                {link.icon && <link.icon size={15} className="text-cyan-400" />}
                <span>{link.label}</span>
                {link.badge && (
                  <span className="ml-1 flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500 text-[11px] font-bold text-black animate-bounce">
                    {link.badge}
                  </span>
                )}
                {active && (
                  <span className="absolute bottom-0 left-2 right-2 h-0.5 rounded-full bg-cyan-400 shadow-cyan-glow" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Action Controls & Utilities */}
        <div className="hidden md:flex items-center gap-3">
          {/* Quick Search Button */}
          <button
            type="button"
            onClick={() => setIsSearchOpen(true)}
            className="flex items-center gap-2 rounded-xl bg-surface-100/90 px-3.5 py-2 text-xs text-white/60 hover:text-white border border-surface-border hover:border-cyan-500/40 transition-all shadow-sm"
          >
            <Search size={14} className="text-cyan-400" />
            <span>Search vehicles, brands...</span>
            <kbd className="rounded bg-surface-200 px-1.5 py-0.5 text-[10px] text-white/40 border border-surface-border font-mono">
              ⌘K
            </kbd>
          </button>

          {/* Unit Toggle Button */}
          <button
            type="button"
            onClick={toggleUnitSystem}
            className="flex items-center gap-1.5 rounded-xl bg-surface-100/90 px-3 py-2 text-xs font-semibold border border-surface-border hover:border-surface-hover text-white transition-all"
            title={`Switch to ${unitSystem === 'metric' ? 'Imperial (mph, hp)' : 'Metric (km/h, kW)'}`}
          >
            <Gauge size={14} className="text-cyan-400" />
            <span className="uppercase text-[11px] font-mono text-cyan-300">
              {unitSystem === 'metric' ? 'Metric (km/h)' : 'Imperial (mph)'}
            </span>
          </button>

          {/* Persistent Compare Shortcut Button */}
          <Link
            href="/compare"
            className="relative flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-4 py-2 text-xs font-bold text-black shadow-cyan-glow hover:opacity-95 transition-transform active:scale-95"
          >
            <Scale size={14} />
            <span>Compare</span>
            {comparisonIds.length > 0 && (
              <span className="ml-1 rounded-full bg-black px-1.5 py-0.2 text-[10px] font-bold text-cyan-400">
                {comparisonIds.length}
              </span>
            )}
          </Link>
        </div>

        {/* Mobile Menu Button */}
        <div className="flex items-center gap-2 lg:hidden">
          <button
            type="button"
            onClick={() => setIsSearchOpen(true)}
            className="rounded-lg bg-surface-100 p-2 text-white/70 hover:text-white"
          >
            <Search size={18} />
          </button>
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="rounded-lg bg-surface-100 p-2 text-white/70 hover:text-white border border-surface-border"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-surface-border bg-surface-100/95 backdrop-blur-2xl px-4 py-6 space-y-4">
          <nav className="flex flex-col space-y-2">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center justify-between rounded-lg px-4 py-3 text-sm font-medium ${
                  isActive(link.href)
                    ? 'bg-cyan-500/10 text-cyan-400 font-semibold border-l-2 border-cyan-400'
                    : 'text-white/80 hover:bg-surface-50'
                }`}
              >
                <div className="flex items-center gap-2">
                  {link.icon && <link.icon size={16} />}
                  <span>{link.label}</span>
                </div>
                {link.badge && (
                  <span className="rounded-full bg-cyan-500 px-2 py-0.5 text-xs font-bold text-black">
                    {link.badge}
                  </span>
                )}
              </Link>
            ))}
          </nav>

          <div className="pt-4 border-t border-surface-border flex items-center justify-between">
            <button
              type="button"
              onClick={toggleUnitSystem}
              className="flex items-center gap-2 text-xs text-white/80 font-mono"
            >
              <Gauge size={14} className="text-cyan-400" />
              <span>Unit: {unitSystem === 'metric' ? 'Metric' : 'Imperial'}</span>
            </button>
            <Link
              href="/compare"
              onClick={() => setMobileMenuOpen(false)}
              className="rounded-lg bg-cyan-500 px-4 py-2 text-xs font-bold text-black"
            >
              Compare ({comparisonIds.length})
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}

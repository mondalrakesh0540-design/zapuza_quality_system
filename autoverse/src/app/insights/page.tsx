'use client';

import React from 'react';
import Link from 'next/link';
import { 
  Zap, 
  Compass, 
  ShieldCheck, 
  Layers, 
  Gauge, 
  BatteryCharging, 
  Wind, 
  ArrowRight,
  BookOpen
} from 'lucide-react';

export default function InsightsPage() {
  const articles = [
    {
      id: 'ev-vs-ice-running-costs',
      title: 'Electric vs Petrol: The Real 5-Year Cost of Ownership in 2026',
      category: 'Efficiency & Economics',
      readTime: '6 min read',
      date: 'September 2024',
      summary: 'Analyzing battery degradation over 150,000 km, commercial DC fast charging tariffs vs petrol pump inflation, brake wear longevity with regenerative braking, and maintenance schedules between ICE transmissions and direct-drive EV inverters.',
      icon: Zap,
      keyPoints: [
        'EV real-world operating costs range between ₹1.2 to ₹1.8 / km compared to ₹7.5 to ₹11.0 / km for petrol.',
        'Modern LFP battery packs retain >82% health after 8 years under controlled thermal management.',
        'High highway DC fast charging costs can narrow the savings gap on cross-country road trips.'
      ]
    },
    {
      id: 'active-aerodynamics-explained',
      title: 'Active Aerodynamics: How Modern Supercars Produce 860+ kg Downforce',
      category: 'Chassis & Aerodynamics',
      readTime: '8 min read',
      date: 'August 2024',
      summary: 'From Porsche 911 GT3 RS electro-hydraulic DRS rear wings to Rimac Nevera active underbody venturi flaps and Ferrari 296 GTB active rear airbrakes: exploring how CFD simulation turns airflow into mechanical grip without aerodynamic drag penalties on the straights.',
      icon: Wind,
      keyPoints: [
        'Active Drag Reduction Systems (DRS) reduce wing stall drag by up to 35% on high-speed straights.',
        'Underbody ground-effect venturi tunnels create suction without increasing frontal drag area.',
        'Airbrake deployment can generate over 0.6G of decelerating aero drag during threshold braking.'
      ]
    },
    {
      id: 'ncap-crash-standards-comparison',
      title: 'Global Crash Standards Decoded: Bharat NCAP vs Euro NCAP vs IIHS',
      category: 'Safety & Regulations',
      readTime: '7 min read',
      date: 'September 2024',
      summary: 'A forensic comparison of crash test protocol speeds: 64 km/h frontal offset deformable barrier tests, 50 km/h side mobile barrier collisions, 29 km/h side pole impacts, electronic stability control (ESC) fitment mandates, and ISOFIX child restraint scoring across India and Europe.',
      icon: ShieldCheck,
      keyPoints: [
        'Bharat NCAP adheres to stringent Global NCAP protocols with localized testing infrastructure in India.',
        'Level 2 ADAS evaluation now carries significant weighting towards achieving maximum 5-star ratings.',
        'Pedestrian safety legform and headform impact compliance is now mandatory across all production trims.'
      ]
    },
    {
      id: 'dual-clutch-vs-torque-converter',
      title: 'DCT vs Torque Converter vs Single-Speed EV: Which Transmission Reigns Supreme?',
      category: 'Powertrain Engineering',
      readTime: '5 min read',
      date: 'July 2024',
      summary: 'Examining shift speeds (Porsche PDK at 80 milliseconds), thermal tolerance in stop-and-go city traffic, heavy towing durability in off-roaders like the Thar Roxx, and why electric vehicles achieve 0-100 sprints with seamless single-speed reduction gears.',
      icon: Gauge,
      keyPoints: [
        'Wet-clutch dual-clutch transmissions offer lightning upshifts but require sophisticated clutch cooling.',
        'Modern 8-speed torque converters (ZF / Aisin) have virtually closed the gearshift latency gap.',
        'Single-speed EV reduction gearboxes eliminate mechanical complexity and shift-shock entirely.'
      ]
    }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      {/* Header */}
      <div className="border-b border-surface-border pb-6">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
          <BookOpen size={14} />
          <span>Automotive Intelligence Hub</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white font-display mt-1">
          Automotive Engineering Insights
        </h1>
        <p className="text-sm text-white/60 mt-1 max-w-2xl">
          Deep-dive technical guides on propulsion architectures, aerodynamic downforce, crash-testing safety protocols, and true ownership economics.
        </p>
      </div>

      {/* Grid of Articles */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {articles.map((art) => (
          <article
            key={art.id}
            className="rounded-3xl bg-surface-100 p-8 border border-surface-border hover:border-cyan-500/40 space-y-6 transition-all hover:shadow-cyan-glow flex flex-col justify-between"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-cyan-500/10 px-3 py-1 text-xs font-bold text-cyan-400 border border-cyan-500/30">
                  <art.icon size={13} />
                  <span>{art.category}</span>
                </span>
                <span className="text-xs text-white/40">{art.readTime} • {art.date}</span>
              </div>

              <h2 className="text-xl font-bold text-white font-display leading-snug">
                {art.title}
              </h2>

              <p className="text-xs sm:text-sm text-white/70 leading-relaxed">
                {art.summary}
              </p>

              <div className="rounded-2xl bg-surface-200/50 p-4 border border-surface-border space-y-2">
                <span className="text-[10px] uppercase tracking-wider text-cyan-400 font-bold block">
                  Key Takeaways:
                </span>
                <ul className="space-y-1.5 text-xs text-white/80">
                  {art.keyPoints.map((pt, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-cyan-400 font-bold mt-0.5">•</span>
                      <span>{pt}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="pt-4 border-t border-surface-border flex items-center justify-between">
              <Link
                href="/cars"
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
              >
                <span>Find Vehicles with this Tech</span>
                <ArrowRight size={13} />
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

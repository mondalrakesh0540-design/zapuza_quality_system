import type { Metadata } from 'next';
import './globals.css';
import { StoreProvider } from '@/lib/store';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import { ComparisonTray } from '@/components/compare/ComparisonTray';
import { SearchModal } from '@/components/search/SearchModal';

export const metadata: Metadata = {
  title: 'AUTOVERSE 3D — Next-Gen 3D Automotive Explorer & Showroom',
  description: 'Explore verified car specifications, compare vehicles side-by-side, and inspect cars in real-time interactive 3D from Indian and international manufacturers.',
  keywords: [
    'Automotive 3D',
    'Car Explorer',
    'Vehicle Comparison',
    'Indian Cars',
    'Electric Vehicles',
    'Supercars',
    'Porsche',
    'Tata Motors',
    'Mahindra',
    'Three.js 3D Cars',
  ],
  authors: [{ name: 'AUTOVERSE 3D Engineering' }],
  openGraph: {
    title: 'AUTOVERSE 3D — Automotive Excellence in 3D',
    description: 'Explore every detail. Compare every specification. Experience cars in 3D.',
    siteName: 'AUTOVERSE 3D',
    locale: 'en_US',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body className="min-h-screen bg-background text-white antialiased flex flex-col selection:bg-cyan-500 selection:text-black">
        <StoreProvider>
          <Navbar />
          <main className="flex-1 w-full">{children}</main>
          <ComparisonTray />
          <SearchModal />
          <Footer />
        </StoreProvider>
      </body>
    </html>
  );
}

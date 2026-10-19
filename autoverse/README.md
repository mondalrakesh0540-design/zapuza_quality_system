# AUTOVERSE 3D — Next-Gen 3D Automotive Explorer Website

**AUTOVERSE 3D** is a next-generation automotive discovery platform that combines an editorial luxury showroom aesthetic with an interactive Three.js / WebGL 3D vehicle inspection engine, comprehensive multi-market specification database, 4-car comparison matrix, and admin data verification workflows.

---

## 🚀 Key Highlights & Capabilities

### 1. Interactive WebGL 3D Vehicle Studio
- **Genuine 3D Procedural Geometries & PBR Materials**: Smoothly renders car chassis, clearcoat automotive paint shaders, tinted glass canopies, forged alloy rims, perforated brake rotors, and performance calipers.
- **Dynamic Paint Finishes**: Instant real-time color switcher across factory metallic, pearl, gloss, and matte options (e.g., Arctic Grey, Cyber Cyan, Rosso Corsa, Stealth Black, Isle of Man Green).
- **Studio Lighting Presets**:
  - `Cyber Studio`: Moody cyan key light and deep blue rim lighting.
  - `Pure Showroom`: Balanced daylight spotlighting with ground reflections.
  - `Golden Sunset`: Warm low-angle rim lighting and amber specular flares.
  - `High Noon Stage`: 6500K inspection illumination.
- **Camera Presets & Controls**: Smooth orbit rotation, pinch/wheel zoom, pan, and one-click camera angles (Front 3/4, Side Profile, Rear 3/4, Top Down, and Reset).
- **Turntable & Wireframe Modes**: Automated smooth showroom rotation and wireframe geometry inspection.
- **Interactive Component Hotspots**: 3D floating markers for:
  - Powertrain (Engine / Electric Motors)
  - Wheels & Ceramic Brakes
  - Active Aerodynamics (DRS Wings, Diffusers)
  - Lighting (HD Matrix LED / Laserlight)
  - Cockpit & Infotainment Screens
  - Chassis & Battery Enclosures
- **Fallback Photo Gallery**: Seamless toggle to high-definition photography on low-power devices.

### 2. Multi-Market Automotive Database
- Covers Indian (Tata Motors, Mahindra, Maruti Suzuki) and International (Porsche, BMW, Tesla, Ferrari, Rimac, Mercedes-AMG, Toyota, Land Rover) manufacturers.
- Support for ICE (Petrol, Diesel), Hybrid, Plug-in Hybrid (PHEV), and pure Electric (EV) powertrains.
- Body styles: SUV, Sedan, Coupe, Sports Car, Supercar, Hypercar, and Off-Road 4x4.
- Every specification includes value, units, market, verification timestamp, and official OEM / NCAP source links.

### 3. Metric & Imperial Unit System
- Instant global toggle between **Metric** (`km/h`, `kW`, `Nm`, `km/L`, `mm`, `kg`, `INR Lakh/Cr`) and **Imperial** (`mph`, `hp`, `lb-ft`, `MPG`, `in`, `lbs`, `USD`).
- Real-time conversion across all specification tables, card strips, and comparison matrices.

### 4. Advanced 4-Vehicle Comparison Matrix
- Compare 2, 3, or 4 vehicles side by side.
- Difference highlight indicators with an optional **"Only Differences"** filter.
- Dynamic URL parameter synchronization (`/compare?cars=porsche-911-gt3-rs,tata-nexon-ev`) for shareable comparisons.
- Persistent comparison tray available site-wide with add/remove controls.

### 5. Multi-Facet Search & Filtering
- Real-time search by brand, model, body type, or fuel type.
- Multi-select brand, body style, and powertrain filters.
- Sorting by Price (Low/High), Power (HP), 0-100 km/h acceleration, and Newest model year.
- Active filter chips with one-click removal and "Clear All".
- Quick-View specification modal on any vehicle card.

### 6. Admin & Data Governance Console (`/admin`)
- Vehicle catalog management with Add Vehicle and Delete operations.
- Verification badge management (Certified vs Pending Audit).
- User-submitted corrections moderation queue with Approve/Reject actions.
- Change audit log with timestamped entries.

---

## 🛠️ Technology Stack

- **Framework**: Next.js 14 (App Router) with TypeScript
- **3D Graphics & WebGL**: Three.js, React Three Fiber (`@react-three/fiber`), Drei (`@react-three/drei`)
- **Styling**: Tailwind CSS with custom automotive design tokens and glassmorphism
- **Icons**: Lucide React
- **Testing**: Node & `tsx` automated unit and data integrity test runner

---

## 💻 Setup & Execution Instructions

### Running from Workspace Root:
```bash
# Run tests
npm test

# Start development server
npm run dev

# Production build
npm run build
```

### Running from `autoverse` Directory:
```bash
cd autoverse

# Install dependencies
npm install

# Run automated tests (69 assertions)
npm test

# Start development server on port 3000
npm run dev

# Create optimized production build
npm run build

# Start production server
npm start
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Automated Test Suite

Run the verified test suite anytime:
```bash
npm test
```
The test suite validates:
1. **Catalog Integrity**: Ensures all vehicles have valid identifiers, positive prices, realistic dimensions, verified sources, and hotspot metadata.
2. **Unit Conversion**: Validates metric to imperial conversions for speed, power, torque, dimensions, weight, and pricing.
3. **Search & Retrieval**: Tests fuzzy search and slug lookup.
4. **Comparison Engine**: Tests difference detection across dissimilar vehicle attributes.

---

## ⚖️ Data Accuracy Statement
AUTOVERSE 3D maintains an authentic, expanding database. All specifications, prices, test scores, and performance metrics are independently verified against manufacturer homologation documentation, Bharat NCAP, Euro NCAP, and official price registries.

export type BodyStyle = 
  | 'SUV'
  | 'Compact SUV'
  | 'Sedan'
  | 'Hatchback'
  | 'Coupe'
  | 'Sports Car'
  | 'Supercar'
  | 'Hypercar'
  | 'Luxury'
  | 'Off-Road'
  | 'MUV'
  | 'MPV';

export type FuelType = 
  | 'Electric'
  | 'Petrol'
  | 'Diesel'
  | 'Hybrid'
  | 'Plug-in Hybrid'
  | 'CNG';

export type TransmissionType =
  | 'Manual'
  | 'Automatic'
  | 'Dual-Clutch (DCT)'
  | 'CVT'
  | 'e-CVT'
  | 'Single-Speed (EV)'
  | 'AMT';

export type DriveType = 'AWD' | 'RWD' | 'FWD' | '4WD';

export type VehicleStatus = 'Production' | 'Historical' | 'Upcoming' | 'Concept';

export type IndiaAvailabilityStatus = 
  | 'Currently Available'
  | 'Upcoming'
  | 'Discontinued'
  | 'Imported on Request'
  | 'Historical';

export type MarketType = 'Global' | 'India' | 'North America' | 'Europe' | 'Japan';

export type PricingStatus = 'verified' | 'estimated' | 'unavailable' | 'expired';

export interface PaintColor {
  id: string;
  name: string;
  hex: string;
  finish: 'Metallic' | 'Matte' | 'Pearl' | 'Gloss';
}

export interface Hotspot {
  id: string;
  title: string;
  category: 'Powertrain' | 'Aerodynamics' | 'Wheels & Brakes' | 'Lighting' | 'Cockpit' | 'Interior' | 'Chassis';
  position: [number, number, number]; // 3D coordinates in scene
  description: string;
  keySpecs?: { label: string; value: string }[];
}

export interface SpecificationSource {
  title: string;
  url: string;
  verificationDate: string;
  confidence?: 'High' | 'Medium' | 'Estimated';
  notes?: string;
}

export interface CityPricing {
  cityName: string;
  stateName: string;
  exShowroomPrice: number;
  rtoRoadTax: number;
  insuranceEstimate: number;
  tcs: number; // 1% for ex-showroom > 10,00,000 INR
  otherCharges: {
    fastag: number;
    registrationAndHandling: number;
    greenCess?: number;
    municipalTax?: number;
  };
  totalOnRoadEstimate: number;
  pricingStatus: PricingStatus;
  effectiveDate: string;
  lastVerifiedDate: string;
  sourceUrl: string;
  notes?: string;
}

export interface VehicleVariant {
  id: string;
  name: string;
  trim: string;
  price: number; // Legacy & fallback support for startingPrice tests
  currency: string;
  transmission: string;
  powerHp: number;
  keyFeatures: string[];
  
  // Enriched India Market Variant Attributes
  exShowroomPrice?: number;
  fuelType?: FuelType;
  transmissionType?: TransmissionType;
  drivetrain?: DriveType;
  engineDisplacementCc?: number;
  torqueNm?: number;
  claimedMileageOrRange?: string;
  seatingCapacity?: number;
  airbagsCount?: number;
  sunroof?: string;
  adasLevel?: string;
  cityPricing?: Record<string, CityPricing>;
  availabilityStatus?: IndiaAvailabilityStatus;
  sourceUrl?: string;
  lastVerifiedDate?: string;
}

export interface BlueprintDimensions {
  overallLengthMm: number;
  overallWidthMm: number;
  overallHeightMm: number;
  wheelbaseMm: number;
  groundClearanceMm: number;
  frontTrackMm: number;
  rearTrackMm: number;
  frontOverhangMm?: number;
  rearOverhangMm?: number;
  turningRadiusM: number;
  bootCapacityL: number;
  fuelTankL?: number;
  tyreSpecification: string;
  wheelRimSizeInches: number;
  schematicType: 'ISO 128 Dimension Schematic' | 'Official Homologation Drawing' | 'CAD Technical Illustration';
  verificationSource: string;
}

export interface VehicleComponent {
  id: string;
  system: 
    | 'Powertrain & Engine'
    | 'Electric Motor & Inverter'
    | 'Battery & Thermal BMS'
    | 'Transmission & Driveline'
    | 'Chassis & Monocoque'
    | 'Suspension Architecture'
    | 'Steering Assembly'
    | 'Braking & ESC'
    | 'Wheels & Performance Rubber'
    | 'Cooling & HVAC Circuits'
    | 'Lighting & Optical Systems'
    | 'Cockpit & CAN Bus Electronics'
    | 'Passive Safety & Restraints';
  name: string;
  subsystem: string;
  supplierOrOem?: string;
  operatingPrinciple: string;
  technicalSpecs: { label: string; value: string }[];
  diagramType: 'schematic' | '3d-highlight' | 'technical-drawing';
  schematicSvgPath?: string;
  diagramDescription: string;
  maintenanceLifecycle: string;
  isVerifiedOem: boolean;
}

export interface Vehicle3DAsset {
  assetId: string;
  assetType: 'procedural-detailed' | 'licensed-glb' | 'cad-demonstrator';
  meshFormat: 'ThreeJS Procedural Geometry' | 'GLTF/GLB' | 'PBR Standard';
  modelScale: [number, number, number];
  coordinateOrientation: string;
  supportedMaterials: string[];
  licenseType: 'Proprietary Autoverse Procedural CAD' | 'OEM Homologation Asset' | 'Editorial Demonstration License';
  assetSource: string;
  verificationStatus: 'Certified Accurate Geometry' | 'Dimensionally Accurate Schematic Demonstration';
  attributionText: string;
  hasInteractiveExplodedView: boolean;
}

export interface VehicleSpecs {
  // Powertrain & Performance
  engineDisplacementCc?: number;
  engineConfiguration?: string; // e.g. "3.0L Twin-Turbo Flat-6"
  cylinders?: number;
  valvesPerCylinder?: number;
  inductionType?: 'Naturally Aspirated' | 'Turbocharged' | 'Twin-Turbocharged' | 'Supercharged' | 'Electric Motor';
  maxPowerHp: number;
  maxPowerKw: number;
  maxPowerRpm?: number;
  maxTorqueNm: number;
  maxTorqueRpm?: string;
  transmission: TransmissionType;
  gearRatios?: string[];
  gears?: number;
  driveType: DriveType;
  acceleration0to100Kmh: number; // in seconds
  topSpeedKmh: number;
  fuelEconomyKmPerL?: number; // for ICE/Hybrid
  emissionsStandard?: string; // e.g. "BS6 Phase 2 / OBD-2"
  co2EmissionsGPerKm?: number;

  // EV Specifics
  batteryCapacityKwh?: number;
  usableBatteryKwh?: number;
  electricRangeKm?: number;
  rangeTestCycle?: 'WLTP' | 'EPA' | 'ARAI' | 'MIDC' | 'Manufacturer Claim';
  maxDcChargingPowerKw?: number;
  dcChargingTime10to80Min?: number;
  acChargingTime0to100Hours?: number;
  chargingConnector?: 'CCS2' | 'Type 2' | 'GB/T' | 'CHAdeMO';
  motorLayout?: string; // e.g. "Dual Permanent Magnet Synchronous Motors"
  batteryWarrantyYears?: number;
  batteryWarrantyKm?: number;

  // Dimensions & Weight
  lengthMm: number;
  widthMm: number;
  heightMm: number;
  wheelbaseMm: number;
  groundClearanceMm: number;
  kerbWeightKg: number;
  grossWeightKg?: number;
  bootCapacityLiters: number;
  seatingCapacity: number;
  doorsCount: number;
  fuelTankCapacityLiters?: number;
  turningRadiusMeters?: number;
  frontTrackMm?: number;
  rearTrackMm?: number;
  frontTyres: string;
  rearTyres: string;

  // Interior & Comfort
  dashboardDisplaySize: string;
  infotainmentScreenSize: string;
  carPlayAndroidAuto: 'Wireless' | 'Wired' | 'Both' | 'None';
  climateControl: string;
  soundSystem: string;
  ambientLighting: string;
  sunroof: 'Panoramic Sunroof' | 'Standard Sunroof' | 'Fixed Glass Roof' | 'Carbon Fiber Roof' | 'None';
  seatUpholstery: string;

  // Safety & Ratings
  airbagsCount: number;
  absEsc: boolean;
  adasLevel: 'Level 0' | 'Level 1' | 'Level 2' | 'Level 2+' | 'Level 3';
  adasFeatures: string[];
  parkingAssist: string;
  ncapRating?: number; // 0 to 5 stars
  ncapAgency?: 'Global NCAP' | 'Euro NCAP' | 'Bharat NCAP' | 'IIHS' | 'NHTSA';
  ncapYear?: number;
  isofix: boolean;

  // Exterior
  lightingTechnology: string;
  wheelSizeInches: number;
  wheelMaterial: string;
  dragCoefficientCd?: number;

  // Ownership & Warranty
  warrantyYears: number;
  warrantyKilometers: number;
  estimatedAnnualServiceCost: number;
  serviceCostCurrency: string;
  serviceIntervalKm?: number;
  serviceIntervalMonths?: number;
}

export interface Vehicle {
  id: string;
  slug: string;
  brandId: string;
  brandName: string;
  brandCountry: string;
  brandLogo: string;
  modelName: string;
  generation: string;
  generationAndFacelift?: string;
  modelYear: number;
  bodyStyle: BodyStyle;
  fuelType: FuelType;
  status: VehicleStatus;
  indiaAvailabilityStatus: IndiaAvailabilityStatus;
  primaryMarket: MarketType;
  
  // Pricing
  startingPrice: number;
  currency: 'INR' | 'USD' | 'EUR' | 'GBP';
  priceType: 'Ex-Showroom' | 'MSRP' | 'Base Estimated';
  priceFormatted: string;
  cityPricing?: Record<string, CityPricing>;
  pricingStatus?: PricingStatus;
  variants: VehicleVariant[];

  // Editorial & Descriptions
  tagline: string;
  overviewDescription: string;
  exteriorHighlights: string[];
  interiorHighlights: string[];
  keyStrengths: string[];
  limitations: string[];

  // Full Specifications
  specs: VehicleSpecs;

  // Technical Blueprint & Components
  blueprint?: BlueprintDimensions;
  components?: VehicleComponent[];

  // Media
  heroImage: string;
  exteriorImages: string[];
  interiorImages: string[];
  colorOptions: PaintColor[];
  
  // 3D Model Configuration & Asset Metadata
  has3D: boolean;
  model3DConfig?: {
    type: 'hypercar' | 'suv' | 'sports-coupe' | 'luxury-sedan' | 'ev-crossover' | 'hatchback' | 'muv';
    defaultColor: string;
    cameraInitialPosition: [number, number, number];
    hotspots: Hotspot[];
  };
  asset3DMetadata?: Vehicle3DAsset;

  // Verification & Sources
  isVerified: boolean;
  verificationDate: string;
  lastAvailabilityVerificationDate?: string;
  verifiedBy: string;
  sources: SpecificationSource[];
  officialUrl?: string;
  officialBrochureUrl?: string;

  // Meta
  viewsCount: number;
  featured: boolean;
  trending: boolean;
}

export interface Brand {
  id: string;
  name: string;
  slug: string;
  country: string;
  flagEmoji: string;
  foundedYear: number;
  headquarters: string;
  parentCompany?: string;
  logo: string;
  heroBanner: string;
  description: string;
  website: string;
  officialIndiaWebsite?: string;
  modelCount: number;
  popularModels: string[];
  isVerified: boolean;
  indiaAssemblyPlant?: string; // e.g. "Chakan, Pune" or "Sanand, Gujarat"
}

export interface ComparisonItem {
  vehicle: Vehicle;
  highlightWins?: { [key: string]: boolean };
}

export interface FilterState {
  searchQuery: string;
  brands: string[];
  bodyStyles: BodyStyle[];
  fuelTypes: FuelType[];
  transmissions: TransmissionType[];
  driveTypes: DriveType[];
  priceRange: [number, number];
  minPowerHp: number;
  minRangeKm: number;
  status: VehicleStatus[];
  availabilityStatus: IndiaAvailabilityStatus[];
  primaryMarket: MarketType[];
  city?: string;
  seatingCapacities: number[];
  has3DOnly: boolean;
  hasBlueprintOnly: boolean;
  sortBy: 'price-asc' | 'price-desc' | 'power-desc' | 'accel-asc' | 'year-desc' | 'popular';
}

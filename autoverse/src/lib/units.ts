export type UnitSystem = 'metric' | 'imperial';

export interface FormattedSpecs {
  speed: string;
  power: string;
  torque: string;
  range: string;
  length: string;
  weight: string;
  economy: string;
}

export function convertSpeed(kmh: number, system: UnitSystem): string {
  if (system === 'imperial') {
    const mph = Math.round(kmh * 0.621371);
    return `${mph} mph`;
  }
  return `${kmh} km/h`;
}

export function convertPower(hp: number, kw: number, system: UnitSystem): string {
  if (system === 'imperial') {
    return `${hp} hp`;
  }
  return `${kw} kW (${hp} hp)`;
}

export function convertTorque(nm: number, system: UnitSystem): string {
  if (system === 'imperial') {
    const lbFt = Math.round(nm * 0.737562);
    return `${lbFt} lb-ft`;
  }
  return `${nm} Nm`;
}

export function convertRange(km: number | undefined, system: UnitSystem): string {
  if (!km) return 'N/A';
  if (system === 'imperial') {
    const miles = Math.round(km * 0.621371);
    return `${miles} miles`;
  }
  return `${km} km`;
}

export function convertDimension(mm: number, system: UnitSystem): string {
  if (system === 'imperial') {
    const inches = (mm / 25.4).toFixed(1);
    return `${inches} in`;
  }
  return `${mm} mm`;
}

export function convertWeight(kg: number, system: UnitSystem): string {
  if (system === 'imperial') {
    const lbs = Math.round(kg * 2.20462);
    return `${lbs.toLocaleString()} lbs`;
  }
  return `${kg.toLocaleString()} kg`;
}

export function convertFuelEconomy(kmPerL: number | undefined, system: UnitSystem): string {
  if (!kmPerL) return 'N/A';
  if (system === 'imperial') {
    // 1 km/L = 2.352145 US MPG
    const mpg = (kmPerL * 2.352145).toFixed(1);
    return `${mpg} MPG`;
  }
  return `${kmPerL.toFixed(1)} km/L`;
}

export function formatPrice(amount: number, currency: string): string {
  if (currency === 'INR') {
    if (amount >= 10000000) {
      return `₹${(amount / 10000000).toFixed(2)} Cr`;
    }
    if (amount >= 100000) {
      return `₹${(amount / 100000).toFixed(2)} Lakh`;
    }
    return `₹${amount.toLocaleString('en-IN')}`;
  }
  if (currency === 'USD') {
    return `$${amount.toLocaleString('en-US')}`;
  }
  if (currency === 'EUR') {
    return `€${amount.toLocaleString('de-DE')}`;
  }
  if (currency === 'GBP') {
    return `£${amount.toLocaleString('en-GB')}`;
  }
  return `${currency} ${amount.toLocaleString()}`;
}

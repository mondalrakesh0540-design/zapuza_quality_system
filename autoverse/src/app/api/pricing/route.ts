import { NextRequest, NextResponse } from 'next/server';
import { calculateCityOnRoadPrice, generateAllCityPricings, INDIAN_CITIES, formatIndianPrice, formatINRStandard } from '@/lib/pricing';
import { FuelType } from '@/types/vehicle';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);

  const exShowroomParam = searchParams.get('exShowroom');
  const fuelTypeParam = searchParams.get('fuelType') as FuelType || 'Petrol';
  const cityParam = searchParams.get('city');

  // If no specific price is queried, return directory of supported cities and RTO tax framework
  if (!exShowroomParam) {
    return NextResponse.json({
      supportedCities: INDIAN_CITIES,
      taxationRules: {
        tcsRule: '1% Tax Collected at Source (TCS) on ex-showroom exceeding ₹10,00,000 under Section 206C(1F)',
        insuranceSchedule: 'Mandatory 1-Year Own Damage (OD) + 3-Year Third Party (TP) under IRDAI guidelines',
        evIncentives: '0% Road Tax in Delhi, Maharashtra, Karnataka, Tamil Nadu, Telangana, and Gujarat under State EV policies',
        fastagAndFees: 'Mandatory RFID FASTag fee ₹600 + statutory registration & smart-card fee ₹1,000'
      }
    });
  }

  const exShowroom = Number(exShowroomParam);
  if (isNaN(exShowroom) || exShowroom <= 0) {
    return NextResponse.json(
      { error: 'Invalid exShowroom price. Please provide a positive numeric value.' },
      { status: 400 }
    );
  }

  if (cityParam) {
    const singleCityPricing = calculateCityOnRoadPrice(
      exShowroom,
      fuelTypeParam,
      cityParam
    );

    return NextResponse.json({
      pricing: singleCityPricing,
      formatted: {
        exShowroomFormatted: formatIndianPrice(singleCityPricing.exShowroomPrice),
        totalOnRoadFormatted: formatIndianPrice(singleCityPricing.totalOnRoadEstimate),
        totalOnRoadStandardINR: formatINRStandard(singleCityPricing.totalOnRoadEstimate)
      }
    });
  }

  // If no city specified, return on-road estimates across all 12 major Indian cities
  const allCities = generateAllCityPricings(exShowroom, fuelTypeParam);
  return NextResponse.json({
    exShowroom,
    fuelType: fuelTypeParam,
    pricings: allCities
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { exShowroom, fuelType = 'Petrol', city = 'delhi' } = body;

    if (!exShowroom || typeof exShowroom !== 'number' || exShowroom <= 0) {
      return NextResponse.json(
        { error: 'Valid positive exShowroom number required in request body.' },
        { status: 400 }
      );
    }

    const pricing = calculateCityOnRoadPrice(exShowroom, fuelType as FuelType, city);

    return NextResponse.json({
      pricing,
      formatted: {
        exShowroomFormatted: formatIndianPrice(pricing.exShowroomPrice),
        totalOnRoadFormatted: formatIndianPrice(pricing.totalOnRoadEstimate),
        totalOnRoadStandardINR: formatINRStandard(pricing.totalOnRoadEstimate)
      }
    });
  } catch (error) {
    return NextResponse.json(
      { error: 'Malformed JSON payload.' },
      { status: 400 }
    );
  }
}

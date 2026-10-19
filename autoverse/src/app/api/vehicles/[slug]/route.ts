import { NextRequest, NextResponse } from 'next/server';
import { getVehicleBySlug, VEHICLES } from '@/data/vehicles';
import { BLUEPRINTS } from '@/data/blueprints';
import { COMPONENTS } from '@/data/components';
import { generateAllCityPricings, calculateCityOnRoadPrice, INDIAN_CITIES } from '@/lib/pricing';

export async function GET(
  request: NextRequest,
  { params }: { params: { slug: string } }
) {
  const { slug } = params;
  const { searchParams } = new URL(request.url);
  const cityParam = searchParams.get('city');

  const vehicle = getVehicleBySlug(slug) || VEHICLES.find(v => v.id === slug);

  if (!vehicle) {
    return NextResponse.json(
      { error: `Vehicle with slug '${slug}' not found in official Indian catalogue.` },
      { status: 404 }
    );
  }

  // Retrieve ISO 128 blueprint technical dimensions
  const blueprint = BLUEPRINTS[vehicle.slug] || vehicle.blueprintDimensions || null;

  // Retrieve component subsystem explorer dataset
  const components = COMPONENTS[vehicle.slug] || vehicle.components || [];

  // Generate on-road pricing across all 12 major Indian cities
  const allCityPricings = generateAllCityPricings(
    vehicle.startingPrice,
    vehicle.fuelType,
    vehicle.officialUrl,
    vehicle.verificationDate
  );

  // If a specific city was requested, calculate or pick it
  let requestedCityPricing = null;
  if (cityParam) {
    requestedCityPricing = calculateCityOnRoadPrice(
      vehicle.startingPrice,
      vehicle.fuelType,
      cityParam,
      vehicle.officialUrl,
      vehicle.verificationDate
    );
  }

  return NextResponse.json({
    vehicle: {
      ...vehicle,
      blueprintDimensions: blueprint,
      components,
      cityPricings: allCityPricings,
      requestedCityPricing
    },
    supportedCities: INDIAN_CITIES
  });
}

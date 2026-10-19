import { NextRequest, NextResponse } from 'next/server';
import { VEHICLES } from '@/data/vehicles';
import { calculateCityOnRoadPrice, INDIAN_CITIES } from '@/lib/pricing';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);

  const search = searchParams.get('search')?.toLowerCase();
  const brand = searchParams.get('brand');
  const body = searchParams.get('body');
  const fuel = searchParams.get('fuel');
  const transmission = searchParams.get('transmission');
  const status = searchParams.get('status');
  const city = searchParams.get('city');
  const seating = searchParams.get('seating') ? Number(searchParams.get('seating')) : null;
  const minPrice = searchParams.get('minPrice') ? Number(searchParams.get('minPrice')) : null;
  const maxPrice = searchParams.get('maxPrice') ? Number(searchParams.get('maxPrice')) : null;
  const minPower = searchParams.get('minPower') ? Number(searchParams.get('minPower')) : null;
  const minRange = searchParams.get('minRange') ? Number(searchParams.get('minRange')) : null;
  const has3d = searchParams.get('has3d') === 'true';
  const hasBlueprint = searchParams.get('hasBlueprint') === 'true';
  const sort = searchParams.get('sort') || 'popular';
  const page = Math.max(1, Number(searchParams.get('page')) || 1);
  const limit = Math.max(1, Math.min(100, Number(searchParams.get('limit')) || 24));

  let results = [...VEHICLES];

  // 1. Text Search across model, brand, tagline, body, fuel
  if (search) {
    results = results.filter((v) => 
      v.modelName.toLowerCase().includes(search) ||
      v.brandName.toLowerCase().includes(search) ||
      v.bodyStyle.toLowerCase().includes(search) ||
      v.fuelType.toLowerCase().includes(search) ||
      v.tagline.toLowerCase().includes(search) ||
      v.variants?.some(vr => vr.name.toLowerCase().includes(search) || vr.trim?.toLowerCase().includes(search))
    );
  }

  // 2. Brand Filter
  if (brand) {
    const brandsList = brand.split(',').map(b => b.trim().toLowerCase());
    results = results.filter(v => 
      brandsList.includes(v.brandId.toLowerCase()) || 
      brandsList.includes(v.brandName.toLowerCase())
    );
  }

  // 3. Body Style Filter
  if (body) {
    const bodiesList = body.split(',').map(b => b.trim().toLowerCase());
    results = results.filter(v => bodiesList.includes(v.bodyStyle.toLowerCase()));
  }

  // 4. Fuel Type Filter
  if (fuel) {
    const fuelsList = fuel.split(',').map(f => f.trim().toLowerCase());
    results = results.filter(v => fuelsList.includes(v.fuelType.toLowerCase()));
  }

  // 5. Availability Status Filter
  if (status) {
    const statusList = status.split(',').map(s => s.trim().toLowerCase());
    results = results.filter(v => 
      v.availabilityStatus && statusList.includes(v.availabilityStatus.toLowerCase())
    );
  }

  // 6. Transmission Filter
  if (transmission) {
    results = results.filter(v => 
      v.specs.transmission.toLowerCase().includes(transmission.toLowerCase()) ||
      v.variants?.some(vr => vr.transmission.toLowerCase().includes(transmission.toLowerCase()))
    );
  }

  // 7. Seating Capacity Filter
  if (seating) {
    results = results.filter(v => v.specs.seatingCapacity >= seating);
  }

  // 8. Price Bracket Filter (INR Ex-Showroom)
  if (minPrice !== null) {
    results = results.filter(v => v.startingPrice >= minPrice);
  }
  if (maxPrice !== null) {
    results = results.filter(v => v.startingPrice <= maxPrice);
  }

  // 9. Minimum Power Filter (hp)
  if (minPower !== null) {
    results = results.filter(v => v.specs.maxPowerHp >= minPower);
  }

  // 10. Minimum Electric Range Filter (km)
  if (minRange !== null) {
    results = results.filter(v => (v.specs.electricRangeKm || 0) >= minRange);
  }

  // 11. 3D Model Availability Filter
  if (has3d) {
    results = results.filter(v => v.has3D);
  }

  // 12. ISO 128 Blueprint Availability Filter
  if (hasBlueprint) {
    results = results.filter(v => Boolean(v.blueprintDimensions));
  }

  // 13. Sorting
  switch (sort) {
    case 'price-asc':
      results.sort((a, b) => a.startingPrice - b.startingPrice);
      break;
    case 'price-desc':
      results.sort((a, b) => b.startingPrice - a.startingPrice);
      break;
    case 'power-desc':
      results.sort((a, b) => b.specs.maxPowerHp - a.specs.maxPowerHp);
      break;
    case 'accel-asc':
      results.sort((a, b) => a.specs.acceleration0to100Kmh - b.specs.acceleration0to100Kmh);
      break;
    case 'range-desc':
      results.sort((a, b) => (b.specs.electricRangeKm || 0) - (a.specs.electricRangeKm || 0));
      break;
    case 'year-desc':
      results.sort((a, b) => b.modelYear - a.modelYear);
      break;
    case 'popular':
    default:
      results.sort((a, b) => b.viewsCount - a.viewsCount);
      break;
  }

  // Optional: City On-Road Calculation Enrichment
  let enrichedResults: any[] = results;
  if (city) {
    enrichedResults = results.map(car => {
      const cityPricing = calculateCityOnRoadPrice(
        car.startingPrice,
        car.fuelType,
        city,
        car.officialUrl,
        car.verificationDate
      );
      return {
        ...car,
        requestedCityPricing: cityPricing
      };
    });
  }

  // Pagination
  const total = enrichedResults.length;
  const totalPages = Math.ceil(total / limit);
  const startIndex = (page - 1) * limit;
  const paginatedResults = enrichedResults.slice(startIndex, startIndex + limit);

  return NextResponse.json({
    total,
    page,
    limit,
    totalPages,
    vehicles: paginatedResults,
  });
}

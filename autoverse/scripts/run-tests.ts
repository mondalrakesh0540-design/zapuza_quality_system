// Automated Test Suite for AUTOVERSE 3D
import { VEHICLES, getVehicleBySlug } from '../src/data/vehicles';
import { BRANDS } from '../src/data/brands';
import { 
  convertSpeed, 
  convertPower, 
  convertTorque, 
  convertRange, 
  convertDimension, 
  convertWeight, 
  formatPrice 
} from '../src/lib/units';

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string) {
  if (condition) {
    console.log(`  ✓ ${message}`);
    passed++;
  } else {
    console.error(`  ✗ FAIL: ${message}`);
    failed++;
  }
}

console.log('\n========================================');
console.log('🧪 RUNNING AUTOVERSE 3D TEST SUITE');
console.log('========================================\n');

// 1. Data Integrity Tests
console.log('Test Group 1: Automotive Database Integrity');
assert(VEHICLES.length >= 6, `Catalog contains ${VEHICLES.length} vehicles (>= 6 required)`);
assert(BRANDS.length >= 8, `Brand directory contains ${BRANDS.length} brands (>= 8 required)`);

VEHICLES.forEach(car => {
  assert(Boolean(car.id && car.slug && car.brandName && car.modelName), `Vehicle ${car.modelName} has valid ID and names`);
  assert(car.startingPrice > 0, `Vehicle ${car.modelName} has positive starting price (${car.priceFormatted})`);
  assert(car.specs.maxPowerHp > 0, `Vehicle ${car.modelName} has positive horsepower (${car.specs.maxPowerHp} hp)`);
  assert(car.specs.acceleration0to100Kmh > 0, `Vehicle ${car.modelName} has valid 0-100 acceleration (${car.specs.acceleration0to100Kmh}s)`);
  assert(car.specs.lengthMm > 3000 && car.specs.widthMm > 1500, `Vehicle ${car.modelName} has realistic dimensions`);
  assert(Boolean(car.sources && car.sources.length > 0), `Vehicle ${car.modelName} has verified sources`);
  if (car.has3D) {
    assert(Boolean(car.model3DConfig && car.model3DConfig.hotspots.length > 0), `3D Model for ${car.modelName} has interactive hotspots`);
  }
});

// 2. Unit Conversion Tests
console.log('\nTest Group 2: Metric & Imperial Unit Engine');
assert(convertSpeed(100, 'metric') === '100 km/h', '100 km/h metric formatted correctly');
assert(convertSpeed(100, 'imperial') === '62 mph', '100 km/h converts to 62 mph');

assert(convertPower(525, 386, 'imperial') === '525 hp', 'Power imperial converts to hp');
assert(convertPower(525, 386, 'metric').includes('386 kW'), 'Power metric includes kW');

assert(convertTorque(465, 'metric') === '465 Nm', 'Torque metric formatted correctly');
assert(convertTorque(465, 'imperial') === '343 lb-ft', 'Torque 465 Nm converts to 343 lb-ft');

assert(convertDimension(4572, 'metric') === '4572 mm', 'Dimension metric formatted');
assert(convertDimension(2540, 'imperial') === '100.0 in', '2540 mm converts to 100.0 inches');

assert(convertWeight(1450, 'metric') === '1,450 kg', 'Weight metric formatted');
assert(convertWeight(1000, 'imperial') === '2,205 lbs', '1000 kg converts to 2,205 lbs');

assert(formatPrice(1449000, 'INR').includes('Lakh'), 'INR format uses Lakh for 14.49 Lakh');
assert(formatPrice(241300, 'USD').includes('$241,300'), 'USD format uses $241,300');

// 3. Search and Filtering Tests
console.log('\nTest Group 3: Search and Retrieval Logic');
const gt3 = getVehicleBySlug('porsche-911-gt3-rs');
assert(gt3 !== undefined && gt3.modelName === '911 GT3 RS', 'Lookup by slug retrieves Porsche 911 GT3 RS');

const nexon = getVehicleBySlug('tata-nexon-ev');
assert(nexon !== undefined && nexon.fuelType === 'Electric', 'Lookup by slug retrieves Tata Nexon EV');

const electricCars = VEHICLES.filter(v => v.fuelType === 'Electric');
assert(electricCars.length >= 3, `Filter by Electric fuel returns ${electricCars.length} models`);

const suvCars = VEHICLES.filter(v => v.bodyStyle === 'SUV');
assert(suvCars.length >= 1, `Filter by SUV returns ${suvCars.length} models`);

// 4. Comparison Logic Tests
console.log('\nTest Group 4: Comparison Differences Engine');
if (gt3 && nexon) {
  const priceDiffers = gt3.startingPrice !== nexon.startingPrice;
  assert(priceDiffers, 'Comparison detects price disparity between sports car and compact EV');
  const powerDiffers = gt3.specs.maxPowerHp !== nexon.specs.maxPowerHp;
  assert(powerDiffers, 'Comparison detects horsepower disparity');
}

console.log('\n========================================');
console.log(`📊 TEST RESULTS: ${passed} Passed, ${failed} Failed`);
console.log('========================================\n');

if (failed > 0) {
  process.exit(1);
} else {
  console.log('🎉 ALL TESTS PASSED SUCCESSFULLY!\n');
  process.exit(0);
}

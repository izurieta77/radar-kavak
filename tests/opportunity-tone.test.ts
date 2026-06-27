import { describe, expect, it } from 'vitest';
import opportunities from '../src/data/opportunities.json';
import type { Opportunity } from '../src/types';
import { opportunityTone } from '../src/lib/opportunityTone';

const typedOpportunities = opportunities as Opportunity[];

describe('opportunityTone', () => {
  it('separates market bargains from regular list vehicles', () => {
    const marketBargain = typedOpportunities.find((item) => item.vehicle.no === 28);
    const listVehicle = typedOpportunities.find((item) => item.vehicle.no === 10);

    expect(marketBargain).toBeDefined();
    expect(listVehicle).toBeDefined();
    expect(opportunityTone(marketBargain!)).toBe('ganga');
    expect(opportunityTone(listVehicle!)).toBe('mi_lista');
  });
});

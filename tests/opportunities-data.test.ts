import { describe, expect, it } from 'vitest';
import opportunities from '../src/data/opportunities.json';

describe('generated opportunities', () => {
  it('contains one opportunity per analyzable non-orange vehicle', () => {
    expect(opportunities).toHaveLength(38);
  });

  it('uses end-of-month target buy prices instead of list prices', () => {
    const x4 = opportunities.find((item) => item.vehicle.no === 5);

    expect(x4?.vehicle.inventoryPrice).toBe(989000);
    expect(x4?.targetBuyPrice).toBe(939000);
    expect(x4?.aggressiveBuyPrice).toBe(919000);
  });

  it('is sorted from highest score to lowest score', () => {
    const scores = opportunities.map((item) => item.score);
    const sorted = [...scores].sort((a, b) => b - a);

    expect(scores).toEqual(sorted);
  });
});


import { describe, expect, it } from 'vitest';
import externalBargains from '../src/data/external_bargains.json';

describe('external bargains feed', () => {
  it('publishes ranked external bargains from the regional scan', () => {
    expect(externalBargains.length).toBeGreaterThanOrEqual(10);
    expect(externalBargains[0].name).toBe('Mercedes Benz Clase GLE');
    expect(externalBargains[0].gapToMedian).toBe(580000);
  });

  it('keeps every external bargain sourced, regional, and below median', () => {
    const allowedRegions = ['CDMX', 'Edomex', 'Queretaro', 'Hidalgo', 'Puebla', 'Morelos'];

    for (const bargain of externalBargains) {
      expect(allowedRegions).toContain(bargain.region);
      expect(bargain.region).not.toBe('Michoacan');
      expect(bargain.url).toMatch(/^https:\/\/www\.seminuevos\.com\/vehicle\//);
      expect(bargain.price).toBeLessThan(bargain.medianComparable);
      expect(bargain.gapToMedian).toBe(bargain.medianComparable - bargain.price);
    }
  });
});

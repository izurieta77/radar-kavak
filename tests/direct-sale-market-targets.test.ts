import { describe, expect, it } from 'vitest';
import directSaleMarketTargets from '../src/data/direct_sale_market_targets.json';

describe('direct-sale market targets', () => {
  it('has at least one current candidate priced below a direct-sale Kavak offer', () => {
    const below = directSaleMarketTargets.filter((target) => target.status === 'below_offer');

    expect(below.length).toBeGreaterThan(0);
    expect(below.every((target) => target.fit === 'same_version_comparable')).toBe(true);
  });

  it('calculates the direct-sale gap as Kavak offer minus market price', () => {
    for (const target of directSaleMarketTargets) {
      expect(target.deltaToKavak).toBe(target.kavakSellOffer - target.candidatePrice);
      expect(target.kavakSellOffer).toBeGreaterThan(0);
      expect(target.candidatePrice).toBeGreaterThan(0);
    }
  });

  it('does not count version or mileage traps as confirmed below-offer deals', () => {
    const rejected = directSaleMarketTargets.filter((target) => target.status === 'rejected');
    const riskyPositive = directSaleMarketTargets.filter(
      (target) => target.deltaToKavak > 0 && target.fit !== 'same_version_comparable'
    );

    expect(rejected.length).toBeGreaterThan(0);
    expect(riskyPositive.every((target) => target.status !== 'below_offer')).toBe(true);
  });

  it('keeps the market-vs-Kavak scan on direct sale only', () => {
    const serialized = JSON.stringify(directSaleMarketTargets).toLowerCase();

    expect(serialized).not.toContain('cambio');
    expect(serialized).not.toContain('trueque');
    expect(serialized).not.toContain('trade');
  });
});

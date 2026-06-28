import { describe, expect, it } from 'vitest';
import directSaleMarketTargets from '../src/data/direct_sale_market_targets.json';

describe('direct-sale market targets', () => {
  it('can surface published below-offer leads only when the seller is not Kavak', () => {
    const belowPublished = directSaleMarketTargets.filter(
      (target) => target.sellerType !== 'kavak' && target.status !== 'rejected' && target.deltaToKavak > 0
    );

    expect(belowPublished.length).toBeGreaterThan(0);
    expect(belowPublished.every((target) => target.sellerType !== 'kavak')).toBe(true);
  });

  it('calculates the direct-sale gap as Kavak offer minus market price', () => {
    for (const target of directSaleMarketTargets) {
      expect(target.deltaToKavak).toBe(target.kavakSellOffer - target.candidatePrice);
      expect(target.kavakSellOffer).toBeGreaterThan(0);
      expect(target.candidatePrice).toBeGreaterThan(0);
    }
  });

  it('does not count version or mileage traps as confirmed below-offer deals', () => {
    const riskyPositive = directSaleMarketTargets.filter((target) => {
      return (
        target.deltaToKavak > 0 &&
        (target.fit !== 'same_version_comparable' || target.sellerType === 'kavak')
      );
    });

    expect(riskyPositive.every((target) => target.status !== 'below_offer')).toBe(true);
  });

  it('blocks listings where Kavak is the seller even when the price is below a Kavak offer', () => {
    const kavakSellerListings = directSaleMarketTargets.filter((target) => target.sellerType === 'kavak');

    expect(kavakSellerListings.length).toBeGreaterThan(0);
    expect(kavakSellerListings.every((target) => target.status === 'blocked_kavak_inventory')).toBe(true);
  });

  it('keeps the market-vs-Kavak scan on direct sale only', () => {
    const serialized = JSON.stringify(directSaleMarketTargets).toLowerCase();

    expect(serialized).not.toContain('cambio');
    expect(serialized).not.toContain('trueque');
    expect(serialized).not.toContain('trade');
  });
});

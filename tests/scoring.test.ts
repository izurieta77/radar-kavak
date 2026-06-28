import { describe, expect, it } from 'vitest';
import { formatKm, formatMoney, negotiationRange, summarizeInventory } from '../src/lib/format';
import inventory from '../src/data/inventario.json';
import opportunitiesData from '../src/data/opportunities.json';
import type { Opportunity } from '../src/types';

const opportunities = opportunitiesData as Opportunity[];

describe('inventory contract', () => {
  it('keeps pink-number rows and excludes only full orange rows', () => {
    const summary = summarizeInventory(inventory);

    expect(summary.total).toBe(48);
    expect(summary.excludedOrange).toBe(10);
    expect(summary.analyzable).toBe(38);
  });
});

describe('format helpers', () => {
  it('formats money and kilometers for Mexican car listings', () => {
    expect(formatMoney(989000)).toBe('$989,000');
    expect(formatMoney(null)).toBe('pendiente');
    expect(formatKm(30215)).toBe('30,215 km');
    expect(formatKm(null)).toBe('sin dato');
  });
});

describe('opportunity scoring', () => {
  it('models end-of-month negotiation against list price', () => {
    expect(negotiationRange(989000)).toEqual({
      listPrice: 989000,
      targetPrice: 939000,
      aggressivePrice: 919000,
      targetDiscount: 50000,
      aggressiveDiscount: 70000
    });
  });

  it('only scores opportunities backed by real kavak or market evidence', () => {
    const violated = opportunities.filter(
      (item) => item.score > 0 && item.kavakOffer == null && item.marketReference == null
    );
    expect(violated).toHaveLength(0);
  });

  it('awards score when kavak offer covers the target buy price', () => {
    const withPositiveSpreadAndKavak = opportunities.filter(
      (item) => item.kavakOffer != null && (item.spread ?? 0) > 0
    );
    expect(withPositiveSpreadAndKavak.length).toBeGreaterThan(0);
    const allScored = withPositiveSpreadAndKavak.every((item) => item.score > 0);
    expect(allScored).toBe(true);
  });

  it('covers all 38 analyzable vehicles', () => {
    expect(opportunities).toHaveLength(38);
  });
});

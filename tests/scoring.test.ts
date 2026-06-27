import { describe, expect, it } from 'vitest';
import { formatKm, formatMoney, negotiationRange, opportunityScore, summarizeInventory } from '../src/lib/format';
import inventory from '../src/data/inventario.json';

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

  it('does not score spreads unless Kavak or market evidence is real', () => {
    const captured = opportunityScore({
      spread: 90000,
      confidence: 0.8,
      kavakStatus: 'capturado',
      hasPublishedMarketEvidence: false
    });
    const pending = opportunityScore({
      spread: 90000,
      confidence: 0.8,
      kavakStatus: 'pendiente',
      hasPublishedMarketEvidence: false
    });
    const market = opportunityScore({
      spread: 90000,
      confidence: 0.8,
      kavakStatus: 'pendiente',
      hasPublishedMarketEvidence: true
    });

    expect(pending).toBe(0);
    expect(captured).toBeGreaterThan(0);
    expect(market).toBeGreaterThan(0);
  });
});

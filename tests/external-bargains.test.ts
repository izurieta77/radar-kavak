import { describe, expect, it } from 'vitest';
import externalBargains from '../src/data/external_bargains.json';
import externalKavakQuotes from '../src/data/external_kavak_quotes.json';

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

  it('attaches Kavak sale-only quotes without using trade-in offers', () => {
    expect(externalKavakQuotes).toHaveLength(externalBargains.length);

    for (const quote of externalKavakQuotes) {
      const bargain = externalBargains.find((item) => item.id === quote.externalId);

      expect(bargain).toBeDefined();
      expect(Object.prototype.hasOwnProperty.call(quote, 'tradeInOffer')).toBe(false);
      if (quote.status === 'capturado') {
        expect(quote.sellOffer).toBeGreaterThan(0);
        expect(quote.url).toMatch(/^https:\/\/www\.kavak\.com\/mx\/v2\/cotizar-auto\/venta-/);
      }
    }

    const x4StyleTrap = externalKavakQuotes.find((quote) => quote.externalId === 'seminuevos-4793320');
    expect(x4StyleTrap?.sellOffer).toBe(411377);
  });

  it('does not mark external Kavak opportunities above list unless direct sale beats published price', () => {
    const quotesById = new Map(externalKavakQuotes.map((quote) => [quote.externalId, quote]));
    const aboveByDirectSale = externalBargains.filter((bargain) => {
      const quote = quotesById.get(bargain.id);
      return quote?.sellOffer != null && quote.sellOffer > bargain.price;
    });

    expect(aboveByDirectSale).toHaveLength(0);
  });
});

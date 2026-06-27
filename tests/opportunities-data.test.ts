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

  it('does not create positive spreads without captured Kavak or published market evidence', () => {
    for (const item of opportunities) {
      const hasCapturedKavak = item.kavakStatus === 'capturado' && item.kavakOffer != null;
      const hasPublishedMarketEvidence = item.evidence.some(
        (evidence) => evidence.status === 'publicado' && evidence.price != null && evidence.url.startsWith('http')
      );

      if (!hasCapturedKavak && !hasPublishedMarketEvidence) {
        expect(item.marketReference).toBeNull();
        expect(item.spread).toBeNull();
        expect(item.score).toBe(0);
      }
    }
  });

  it('keeps the captured Kavak offer for the quoted BMW X4', () => {
    const quotedX4 = opportunities.find((item) => item.vehicle.no === 29);
    const kavakEvidence = quotedX4?.evidence.find((evidence) => evidence.source === 'Kavak');

    expect(quotedX4?.kavakStatus).toBe('capturado');
    expect(quotedX4?.kavakOffer).toBe(853289);
    expect(kavakEvidence?.price).toBe(853289);
    expect(kavakEvidence?.url).toContain('kavak.com/mx/v2/cotizar-auto/venta-multi-oferta-auto');
    expect(quotedX4?.notes).toContain('Kavak venta directa capturado: $853,289; cambio/trueque: $873,663; prestamo: $600,000; vigente hasta 2026-07-05.');
  });

  it('has an explicit Kavak result for every analyzable vehicle', () => {
    expect(opportunities.some((item) => item.kavakStatus === 'pendiente')).toBe(false);
    expect(opportunities.filter((item) => item.kavakStatus === 'capturado')).not.toHaveLength(0);
    expect(opportunities.find((item) => item.vehicle.no === 47)?.kavakStatus).toBe('solo_prestamo');
    expect(opportunities.find((item) => item.vehicle.no === 4)?.kavakStatus).toBe('modelo_no_disponible');
  });

  it('adds several text-exact market references for every vehicle', () => {
    for (const item of opportunities) {
      const literalName = `${item.vehicle.brand} ${item.vehicle.model} ${item.vehicle.year}`;
      const sourceNames = item.marketReferences.map((reference) => reference.source);

      expect(item.marketReferences.length).toBeGreaterThanOrEqual(4);
      expect(sourceNames).toContain('Facebook Marketplace');
      expect(sourceNames).toContain('MercadoLibre');
      expect(sourceNames).toContain('Kavak Catalogo');
      expect(sourceNames).toContain('Google');
      expect(item.marketReferences.every((reference) => reference.query === literalName)).toBe(true);
    }
  });

  it('keeps market references priced only when there is verifiable evidence', () => {
    for (const item of opportunities) {
      for (const reference of item.marketReferences) {
        if (reference.price != null) {
          expect(reference.status).toMatch(/publicado|captura/);
          expect(reference.url).toMatch(/^https?:\/\//);
          expect(reference.evidenceType).toMatch(/html|captura|manual/);
        }
      }
    }
  });
});

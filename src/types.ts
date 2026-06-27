export type KavakStatus = 'pendiente' | 'estimado' | 'capturado' | 'solo_prestamo' | 'modelo_no_disponible';

export interface InventoryVehicle {
  page: number;
  no: number;
  brand: string;
  model: string;
  year: number;
  kilometers: number | null;
  exteriorColor: string;
  interiorColor: string;
  inventoryPrice: number | null;
  invoiceTax: string;
  excludedOrange: boolean;
  pinkNumberCell: boolean;
}

export interface MarketEvidence {
  source: string;
  label: string;
  url: string;
  price: number | null;
  kilometers: number | null;
  zone: 'Toluca' | 'CDMX' | 'Metepec' | 'Nacional';
  status: 'publicado' | 'captura' | 'capturado' | 'solo_prestamo' | 'modelo_no_disponible' | 'asistido' | 'pendiente';
  observedAt?: string;
  publicationId?: string;
  query?: string;
  evidenceType?: 'html' | 'captura' | 'manual' | 'busqueda';
  screenshot?: string;
}

export interface Opportunity {
  vehicle: InventoryVehicle;
  kavakStatus: KavakStatus;
  kavakOffer: number | null;
  kavakTradeOffer: number | null;
  kavakLoanOffer: number | null;
  kavakSellOfferType: string | null;
  marketReference: number | null;
  targetBuyPrice: number | null;
  aggressiveBuyPrice: number | null;
  spread: number | null;
  aggressiveSpread: number | null;
  confidence: number;
  score: number;
  marketReferences: MarketEvidence[];
  evidence: MarketEvidence[];
  notes: string[];
}

export interface NegotiationRange {
  listPrice: number;
  targetPrice: number;
  aggressivePrice: number;
  targetDiscount: number;
  aggressiveDiscount: number;
}

export interface InventorySummary {
  total: number;
  excludedOrange: number;
  analyzable: number;
}

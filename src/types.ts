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
  marketPriceRange: MarketPriceRange | null;
  targetBuyPrice: number | null;
  aggressiveBuyPrice: number | null;
  spread: number | null;
  aggressiveSpread: number | null;
  confidence: number;
  score: number;
  dealAnalysis: DealAnalysis;
  marketReferences: MarketEvidence[];
  evidence: MarketEvidence[];
  notes: string[];
}

export interface ExternalBargain {
  id: string;
  rank: number;
  source: string;
  observedAt: string;
  region: 'CDMX' | 'Edomex' | 'Queretaro' | 'Hidalgo' | 'Puebla' | 'Morelos';
  city: string;
  year: number;
  name: string;
  version: string;
  km: number | null;
  price: number;
  medianComparable: number;
  gapToMedian: number;
  gapPct: number;
  compCount: number;
  url: string;
  why: string;
}

export interface MarketPriceRange {
  low: number;
  mid: number;
  high: number;
  count: number;
}

export interface DealAnalysis {
  kavakBestOffer: number | null;
  kavakBestOfferType: 'venta' | 'cambio' | null;
  kavakVsList: number | null;
  kavakVsListPct: number | null;
  marketLowVsList: number | null;
  marketMidVsList: number | null;
  marketHighVsList: number | null;
  marketLowVsTarget: number | null;
  marketMidVsTarget: number | null;
  marketHighVsTarget: number | null;
  marketLowVsAggressive: number | null;
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

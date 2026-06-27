export type KavakStatus = 'pendiente' | 'estimado' | 'capturado';

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
  status: 'scrapeable' | 'asistido' | 'pendiente';
}

export interface Opportunity {
  vehicle: InventoryVehicle;
  kavakStatus: KavakStatus;
  kavakOffer: number | null;
  marketReference: number | null;
  targetBuyPrice: number | null;
  aggressiveBuyPrice: number | null;
  spread: number | null;
  aggressiveSpread: number | null;
  confidence: number;
  score: number;
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

import type { InventorySummary, InventoryVehicle, KavakStatus, NegotiationRange } from '../types';

export function formatMoney(value: number | null): string {
  if (value == null) return 'pendiente';
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    maximumFractionDigits: 0
  }).format(value);
}

export function formatKm(value: number | null): string {
  if (value == null) return 'sin dato';
  return `${new Intl.NumberFormat('es-MX').format(value)} km`;
}

export function summarizeInventory(inventory: InventoryVehicle[]): InventorySummary {
  const excludedOrange = inventory.filter((vehicle) => vehicle.excludedOrange).length;
  return {
    total: inventory.length,
    excludedOrange,
    analyzable: inventory.length - excludedOrange
  };
}

export function negotiationRange(
  listPrice: number,
  targetDiscount = 50000,
  aggressiveDiscount = 70000
): NegotiationRange {
  return {
    listPrice,
    targetPrice: Math.max(0, listPrice - targetDiscount),
    aggressivePrice: Math.max(0, listPrice - aggressiveDiscount),
    targetDiscount,
    aggressiveDiscount
  };
}

export function statusLabel(status: KavakStatus): string {
  if (status === 'capturado') return 'capturado';
  if (status === 'solo_prestamo') return 'solo prestamo';
  if (status === 'modelo_no_disponible') return 'sin modelo';
  if (status === 'estimado') return 'estimado';
  return 'pendiente';
}

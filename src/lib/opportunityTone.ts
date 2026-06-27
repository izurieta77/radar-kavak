import type { Opportunity } from '../types';

export type OpportunityTone = 'mi_lista' | 'ganga';

export function opportunityTone(item: Opportunity): OpportunityTone {
  return (item.dealAnalysis.marketLowVsTarget ?? 0) > 0 ? 'ganga' : 'mi_lista';
}

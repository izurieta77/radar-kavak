import { useMemo, useState } from 'react';
import {
  BadgeDollarSign,
  Car,
  CircleDot,
  ExternalLink,
  Filter,
  Github,
  Globe2,
  Search,
  ShieldCheck,
  TrendingUp
} from 'lucide-react';
import opportunitiesData from './data/opportunities.json';
import inventoryData from './data/inventario.json';
import type { Opportunity } from './types';
import { formatKm, formatMoney, statusLabel, summarizeInventory } from './lib/format';
import { opportunityTone } from './lib/opportunityTone';

const opportunities = opportunitiesData as Opportunity[];
const workflowItems = [
  { label: 'Inventario', Icon: Car },
  { label: 'Kavak', Icon: BadgeDollarSign },
  { label: 'Mercado', Icon: Globe2 },
  { label: 'Oportunidades', Icon: TrendingUp }
] as const;

function confidenceLabel(confidence: number): string {
  if (confidence >= 0.85) return 'alta';
  if (confidence >= 0.65) return 'media';
  return 'baja';
}

function kavakDisplay(item: Opportunity): string {
  if (item.kavakOffer != null) return formatMoney(item.kavakOffer);
  if (item.kavakStatus === 'solo_prestamo' && item.kavakLoanOffer != null) {
    return `Prestamo ${formatMoney(item.kavakLoanOffer)}`;
  }
  return statusLabel(item.kavakStatus);
}

function marketDisplay(item: Opportunity): string {
  if (item.marketPriceRange != null) {
    return `${formatMoney(item.marketPriceRange.low)} - ${formatMoney(item.marketPriceRange.high)}`;
  }
  return item.marketReferences[0]?.query ?? `${item.vehicle.brand} ${item.vehicle.model}`;
}

function spreadDisplay(item: Opportunity): string {
  return item.spread != null ? formatMoney(item.spread) : 'sin spread';
}

function toneLabel(item: Opportunity): string {
  return opportunityTone(item) === 'ganga' ? 'Ganga mercado' : 'Mi lista';
}

function referencePriceLabel(reference: Opportunity['marketReferences'][number]): string {
  if (reference.price != null) return formatMoney(reference.price);
  return reference.evidenceType === 'captura' ? 'precio en captura' : 'buscar exacto';
}

function deltaLabel(value: number | null): string {
  if (value == null) return 'sin dato';
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${formatMoney(value)}`;
}

function App() {
  const [selectedNo, setSelectedNo] = useState(opportunities[0]?.vehicle.no ?? 0);
  const [query, setQuery] = useState('');
  const [onlyPositive, setOnlyPositive] = useState(false);

  const summary = summarizeInventory(inventoryData);
  const selected = opportunities.find((item) => item.vehicle.no === selectedNo) ?? opportunities[0];
  const selectedTone = opportunityTone(selected);
  const filtered = useMemo(() => {
    const text = query.trim().toLowerCase();
    return opportunities.filter((item) => {
      const vehicle = item.vehicle;
      const matchesText = `${vehicle.brand} ${vehicle.model} ${vehicle.year}`.toLowerCase().includes(text);
      const matchesSpread = !onlyPositive || (item.spread ?? 0) > 0;
      return matchesText && matchesSpread;
    });
  }, [query, onlyPositive]);

  const kavakResults = opportunities.filter((item) => item.kavakStatus !== 'pendiente').length;
  const kavakSaleOffers = opportunities.filter((item) => item.kavakOffer != null).length;
  const loanOnly = opportunities.filter((item) => item.kavakStatus === 'solo_prestamo').length;
  const noModel = opportunities.filter((item) => item.kavakStatus === 'modelo_no_disponible').length;
  const marketRefs = opportunities.filter((item) => item.marketReference != null).length;
  const pricedReferences = opportunities.reduce(
    (sum, item) => sum + item.marketReferences.filter((reference) => reference.price != null).length,
    0
  );
  const positive = opportunities.filter((item) => (item.spread ?? 0) > 0);
  const publishedMargin = positive.reduce((sum, item) => sum + (item.spread ?? 0), 0);
  const kavakAboveList = opportunities
    .filter((item) => (item.dealAnalysis.kavakVsList ?? -Infinity) > 0)
    .sort((a, b) => (b.dealAnalysis.kavakVsList ?? -Infinity) - (a.dealAnalysis.kavakVsList ?? -Infinity));
  const closestKavak = [...opportunities]
    .filter((item) => item.dealAnalysis.kavakBestOffer != null)
    .sort((a, b) => (b.dealAnalysis.kavakVsList ?? -Infinity) - (a.dealAnalysis.kavakVsList ?? -Infinity))
    .slice(0, 5);
  const floorBargains = [...opportunities]
    .filter((item) => item.dealAnalysis.marketLowVsTarget != null)
    .sort((a, b) => (b.dealAnalysis.marketLowVsTarget ?? -Infinity) - (a.dealAnalysis.marketLowVsTarget ?? -Infinity))
    .slice(0, 5);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">RK</div>
          <div>
            <strong>Radar Kavak</strong>
            <span>Arbitraje seminuevos</span>
          </div>
        </div>
        <nav className="workflow">
          {workflowItems.map(({ label, Icon }) => (
            <button className={label === 'Oportunidades' ? 'active' : ''} key={label}>
              <Icon size={17} />
              {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={16} />
          <p>Captcha y OTP se resuelven manualmente. No se crean citas ni se aceptan operaciones.</p>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>Oportunidades fin de mes</h1>
            <p>Azul: tu lista y Kavak. Amarillo: gangas detectadas contra piso real de mercado.</p>
          </div>
          <div className="status-row">
            <span className="status-chip muted">
              <Github size={15} />
              GitHub local
            </span>
            <span className="status-chip ok">
              <Globe2 size={15} />
              Netlify auth OK
            </span>
          </div>
        </header>

        <section className="kpi-grid">
          <div className="kpi kpi-lista">
            <span>Analizables</span>
            <strong>{summary.analyzable}</strong>
            <small>{summary.total} total, {summary.excludedOrange} naranjas fuera</small>
          </div>
          <div className="kpi kpi-lista">
            <span>Resultados Kavak</span>
            <strong>{kavakResults}</strong>
            <small>{kavakSaleOffers} venta, {loanOnly} solo prestamo, {noModel} sin modelo/version</small>
          </div>
          <div className="kpi kpi-ganga">
            <span>Mercado publicado</span>
            <strong>{marketRefs}</strong>
            <small>{pricedReferences} precios con URL; el resto abre busqueda textual exacta</small>
          </div>
          <div className="kpi kpi-ganga accent">
            <span>Margen potencial</span>
            <strong>{formatMoney(publishedMargin)}</strong>
            <small>Contra compra objetivo -50k</small>
          </div>
        </section>

        <section className="analysis-grid">
          <div className="analysis-panel panel-lista">
            <span>Kavak arriba de lista</span>
            <strong>
              {kavakAboveList.length
                ? `${kavakAboveList[0].vehicle.brand} ${kavakAboveList[0].vehicle.model}`
                : 'Ninguno venta directa'}
            </strong>
            <small>
              {kavakAboveList.length
                ? `${deltaLabel(kavakAboveList[0].dealAnalysis.kavakVsList)} con ${kavakAboveList[0].dealAnalysis.kavakBestOfferType}`
                : 'Solo cuentan venta/cambio reales capturados.'}
            </small>
          </div>
          <div className="analysis-panel panel-lista">
            <span>Mas cerca de lista</span>
            {closestKavak.map((item) => (
              <button key={item.vehicle.no} onClick={() => setSelectedNo(item.vehicle.no)}>
                <strong>#{item.vehicle.no} {item.vehicle.brand} {item.vehicle.model}</strong>
                <small>{deltaLabel(item.dealAnalysis.kavakVsList)} vs lista - {item.dealAnalysis.kavakBestOfferType}</small>
              </button>
            ))}
          </div>
          <div className="analysis-panel panel-ganga">
            <span>Gangas por piso de mercado</span>
            {floorBargains.map((item) => (
              <button key={item.vehicle.no} onClick={() => setSelectedNo(item.vehicle.no)}>
                <strong>#{item.vehicle.no} {item.vehicle.brand} {item.vehicle.model}</strong>
                <small>{deltaLabel(item.dealAnalysis.marketLowVsTarget)} vs compra obj. - piso {formatMoney(item.marketPriceRange?.low ?? null)}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="content-grid">
          <div className="table-panel">
            <div className="panel-toolbar">
              <label className="search-box">
                <Search size={16} />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Buscar marca, modelo o anio"
                />
              </label>
              <button className={onlyPositive ? 'toggle active' : 'toggle'} onClick={() => setOnlyPositive(!onlyPositive)}>
                <Filter size={15} />
                Spread positivo
              </button>
            </div>

            <div className="opportunity-table">
              <div className="table-head">
                <span>Auto</span>
                <span>Lista</span>
                <span>Compra obj.</span>
                <span>Kavak</span>
                <span>Mercado</span>
                <span>Spread</span>
              </div>
              {filtered.map((item) => {
                const tone = opportunityTone(item);
                return (
                  <button
                    className={[
                      'table-row',
                      tone === 'ganga' ? 'tone-ganga' : 'tone-lista',
                      item.vehicle.no === selected.vehicle.no ? 'selected' : ''
                    ].filter(Boolean).join(' ')}
                    key={item.vehicle.no}
                    onClick={() => setSelectedNo(item.vehicle.no)}
                  >
                    <span>
                      <strong>{item.vehicle.brand} {item.vehicle.model}</strong>
                      <small>{item.vehicle.year} - {formatKm(item.vehicle.kilometers)}</small>
                      <small className={`tone-badge ${tone === 'ganga' ? 'tone-badge-ganga' : 'tone-badge-lista'}`}>
                        {toneLabel(item)}
                      </small>
                    </span>
                    <span>{formatMoney(item.vehicle.inventoryPrice)}</span>
                    <span>
                      <strong>{formatMoney(item.targetBuyPrice)}</strong>
                      <small>agresivo {formatMoney(item.aggressiveBuyPrice)}</small>
                    </span>
                    <span>
                      <strong>{kavakDisplay(item)}</strong>
                      <small>{statusLabel(item.kavakStatus)}</small>
                    </span>
                    <span>
                      <strong>{marketDisplay(item)}</strong>
                      <small>{item.marketPriceRange == null ? 'busqueda exacta' : `medio ${formatMoney(item.marketPriceRange.mid)}`}</small>
                    </span>
                    <span className={(item.spread ?? 0) > 0 ? 'spread good' : 'spread muted'}>
                      {spreadDisplay(item)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <aside className={`detail-panel ${selectedTone === 'ganga' ? 'tone-ganga-panel' : 'tone-lista-panel'}`}>
            <div className="detail-title">
              <CircleDot size={18} />
              <div>
                <h2>{selected.vehicle.brand} {selected.vehicle.model}</h2>
                <p>{selected.vehicle.year} - {formatKm(selected.vehicle.kilometers)} - #{selected.vehicle.no}</p>
                <span className={`tone-badge ${selectedTone === 'ganga' ? 'tone-badge-ganga' : 'tone-badge-lista'}`}>
                  {toneLabel(selected)}
                </span>
              </div>
            </div>

            <div className="price-stack">
              <div>
                <span>Lista PDF</span>
                <strong>{formatMoney(selected.vehicle.inventoryPrice)}</strong>
              </div>
              <div>
                <span>Compra objetivo</span>
                <strong>{formatMoney(selected.targetBuyPrice)}</strong>
              </div>
              {selected.kavakOffer != null && (
                <div>
                  <span>Kavak venta</span>
                  <strong>{formatMoney(selected.kavakOffer)}</strong>
                </div>
              )}
              {selected.kavakOffer == null && (
                <div>
                  <span>Kavak resultado</span>
                  <strong>{kavakDisplay(selected)}</strong>
                </div>
              )}
              {selected.kavakTradeOffer != null && (
                <div>
                  <span>Kavak cambio</span>
                  <strong>{formatMoney(selected.kavakTradeOffer)}</strong>
                </div>
              )}
              {selected.marketReference != null && (
                <div>
                  <span>Mercado alto</span>
                  <strong>{formatMoney(selected.marketReference)}</strong>
                </div>
              )}
              {selected.marketPriceRange != null && (
                <>
                  <div>
                    <span>Mercado bajo</span>
                    <strong>{formatMoney(selected.marketPriceRange.low)}</strong>
                  </div>
                  <div>
                    <span>Mercado medio</span>
                    <strong>{formatMoney(selected.marketPriceRange.mid)}</strong>
                  </div>
                </>
              )}
              <div>
                <span>Kavak vs lista</span>
                <strong className={(selected.dealAnalysis.kavakVsList ?? 0) > 0 ? 'good-text' : ''}>
                  {deltaLabel(selected.dealAnalysis.kavakVsList)}
                </strong>
              </div>
              <div>
                <span>Piso mercado vs objetivo</span>
                <strong className={(selected.dealAnalysis.marketLowVsTarget ?? 0) > 0 ? 'good-text' : ''}>
                  {deltaLabel(selected.dealAnalysis.marketLowVsTarget)}
                </strong>
              </div>
              <div>
                <span>Spread objetivo</span>
                <strong className={(selected.spread ?? 0) > 0 ? 'good-text' : ''}>{spreadDisplay(selected)}</strong>
              </div>
            </div>

            <div className="confidence">
              <span>Confianza {confidenceLabel(selected.confidence)}</span>
              <div>
                <i style={{ width: `${Math.round(selected.confidence * 100)}%` }} />
              </div>
            </div>

            <section className="detail-section">
              <h3>Referencias por pagina</h3>
              {selected.marketReferences.slice(0, 12).map((reference) => (
                <a href={reference.url} key={`${reference.source}-${reference.label}-${reference.url}`} target="_blank" rel="noreferrer">
                  <span>
                    <strong>{reference.source}: {referencePriceLabel(reference)}</strong>
                    <small>{reference.query} - {reference.status} - {reference.evidenceType ?? 'manual'}</small>
                  </span>
                  <ExternalLink size={15} />
                </a>
              ))}
            </section>

            <section className="detail-section">
              <h3>Evidencia</h3>
              {selected.evidence.slice(0, 5).map((evidence) => (
                <a href={evidence.url} key={`${evidence.source}-${evidence.label}`} target="_blank" rel="noreferrer">
                  <span>
                    <strong>{evidence.label}</strong>
                    <small>{evidence.source} - {evidence.zone} - {evidence.status}</small>
                  </span>
                  <ExternalLink size={15} />
                </a>
              ))}
            </section>

            <section className="detail-section notes">
              <h3>Notas</h3>
              {selected.notes.map((note) => (
                <p key={note}>{note}</p>
              ))}
            </section>
          </aside>
        </section>
      </main>
    </div>
  );
}

export default App;

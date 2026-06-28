import { useMemo, useState } from 'react';
import {
  AlertTriangle,
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
import externalBargainsData from './data/external_bargains.json';
import externalKavakQuotesData from './data/external_kavak_quotes.json';
import directSaleMarketTargetsData from './data/direct_sale_market_targets.json';
import inventoryData from './data/inventario.json';
import type { DirectSaleMarketTarget, ExternalBargain, ExternalKavakQuote, Opportunity } from './types';
import { formatKm, formatMoney, statusLabel, summarizeInventory } from './lib/format';
import { opportunityTone } from './lib/opportunityTone';

const opportunities = opportunitiesData as Opportunity[];
const externalBargains = externalBargainsData as ExternalBargain[];
const externalKavakQuotes = externalKavakQuotesData as ExternalKavakQuote[];
const directSaleMarketTargets = directSaleMarketTargetsData as DirectSaleMarketTarget[];
const externalKavakById = new Map(externalKavakQuotes.map((quote) => [quote.externalId, quote]));
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

function externalKavakDisplay(quote: ExternalKavakQuote | undefined): string {
  if (quote?.sellOffer != null) return formatMoney(quote.sellOffer);
  if (quote?.status === 'solo_prestamo') return 'sin venta directa';
  if (quote?.status === 'requiere_version') return 'requiere version';
  return 'pendiente';
}

function externalKavakDetail(quote: ExternalKavakQuote | undefined, price: number): string {
  if (quote?.sellOffer != null) {
    return `${deltaLabel(quote.sellOffer - price)} vs precio publicado`;
  }
  if (quote?.loanOffer != null) return `solo prestamo ${formatMoney(quote.loanOffer)}`;
  return quote?.reason ?? 'sin resultado Kavak';
}

function marketTargetStatusLabel(item: DirectSaleMarketTarget): string {
  if (item.status === 'below_offer') return 'Abajo confirmado';
  if (item.status === 'near_offer') return 'Muy cerca';
  if (item.status === 'needs_quote') {
    return item.deltaToKavak > 0 ? 'Abajo, cotizar' : 'Cotizar exacto';
  }
  if (item.status === 'blocked_kavak_inventory') return 'Bloqueado Kavak';
  return 'No usar';
}

function marketTargetFitLabel(fit: DirectSaleMarketTarget['fit']): string {
  if (fit === 'same_version_comparable') return 'version comparable';
  if (fit === 'same_version_higher_km') return 'misma version, km distinto';
  if (fit === 'same_model_unquoted') return 'mismo modelo, falta Kavak';
  if (fit === 'kavak_inventory_not_operable') return 'vendedor Kavak';
  return 'version/precio dudoso';
}

function marketTargetDeltaLabel(item: DirectSaleMarketTarget): string {
  if (item.deltaToKavak >= 0) return `${formatMoney(item.deltaToKavak)} abajo de Kavak`;
  return `${formatMoney(Math.abs(item.deltaToKavak))} arriba de Kavak`;
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
  const DISCOUNT_40K = 40_000;
  const discount40kRows = opportunities
    .filter((item) => item.vehicle.inventoryPrice != null && item.kavakOffer != null)
    .map((item) => {
      const adjustedPrice = item.vehicle.inventoryPrice! - DISCOUNT_40K;
      const gap = adjustedPrice - item.kavakOffer!;
      return { item, adjustedPrice, gap };
    })
    .sort((a, b) => a.gap - b.gap);
  const discount40kBelowKavak = discount40kRows.filter((row) => row.gap <= 0);
  const discount40kAboveKavak = discount40kRows.filter((row) => row.gap > 0);

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
  const externalGapTotal = externalBargains.reduce((sum, item) => sum + item.gapToMedian, 0);
  const externalTop = externalBargains[0];
  const externalSaleQuotes = externalKavakQuotes.filter((quote) => quote.sellOffer != null);
  const externalAboveList = externalBargains.filter((deal) => {
    const quote = externalKavakById.get(deal.id);
    return quote?.sellOffer != null && quote.sellOffer > deal.price;
  });
  const externalClosestSale = [...externalBargains]
    .filter((deal) => externalKavakById.get(deal.id)?.sellOffer != null)
    .sort((a, b) => {
      const quoteA = externalKavakById.get(a.id);
      const quoteB = externalKavakById.get(b.id);
      return (quoteB?.sellOffer ?? 0) - b.price - ((quoteA?.sellOffer ?? 0) - a.price);
    })[0];
  const belowDirectSale = directSaleMarketTargets.filter((target) => target.status === 'below_offer');
  const belowPublished = directSaleMarketTargets.filter(
    (target) => target.sellerType !== 'kavak' && target.status !== 'rejected' && target.deltaToKavak > 0
  );
  const nearDirectSale = directSaleMarketTargets.filter((target) => target.status === 'near_offer');
  const needsExactQuote = directSaleMarketTargets.filter((target) => target.status === 'needs_quote');
  const blockedKavakInventory = directSaleMarketTargets.filter((target) => target.status === 'blocked_kavak_inventory');
  const rejectedMarketTargets = directSaleMarketTargets.filter((target) => target.status === 'rejected');
  const marketTargetBest = directSaleMarketTargets
    .filter((target) => target.sellerType !== 'kavak' && target.status !== 'rejected')
    .sort((a, b) => b.deltaToKavak - a.deltaToKavak)[0];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img src="/izu-dynamics-logo.jpg" alt="IZU Dynamics" className="brand-logo" />
          <span className="brand-tagline">Arbitraje seminuevos</span>
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
            <h1>IZU Dynamics · Radar</h1>
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
                ? `${deltaLabel(kavakAboveList[0].dealAnalysis.kavakVsList)} con venta directa`
                : 'Solo cuenta venta directa capturada.'}
            </small>
          </div>
          <div className="analysis-panel panel-lista">
            <span>Mas cerca de lista</span>
            {closestKavak.map((item) => (
              <button key={item.vehicle.no} onClick={() => setSelectedNo(item.vehicle.no)}>
                <strong>#{item.vehicle.no} {item.vehicle.brand} {item.vehicle.model}</strong>
                <small>{deltaLabel(item.dealAnalysis.kavakVsList)} vs lista - venta directa</small>
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

        <section className="discount-section" aria-labelledby="discount-title">
          <div className="section-heading">
            <div>
              <span>Simulador de negociación</span>
              <h2 id="discount-title">Rebaja -$40,000 de lista · ¿Quién queda abajo de Kavak?</h2>
              <p>
                Precio ajustado = lista PDF menos $40,000. Verde = por debajo de la oferta Kavak (spread inmediato).
                Amarillo = sigue arriba pero ya muy cerca. Ordenado de mejor a peor.
              </p>
            </div>
            <div className="scan-summary direct-summary">
              <strong>{discount40kBelowKavak.length}</strong>
              <span>abajo de Kavak con -40k</span>
              <small>
                {discount40kAboveKavak.length} siguen arriba ·{' '}
                {discount40kRows.length} con cotización Kavak activa
              </small>
            </div>
          </div>

          <div className="discount-table">
            <div className="discount-head">
              <span>#</span>
              <span>Vehículo</span>
              <span>Lista PDF</span>
              <span>Lista −40k</span>
              <span>Kavak venta</span>
              <span>Gap vs Kavak</span>
            </div>
            {discount40kRows.map(({ item, adjustedPrice, gap }, rank) => {
              const isBelow = gap <= 0;
              const isNear = !isBelow && gap <= 60_000;
              return (
                <button
                  key={item.vehicle.no}
                  className={[
                    'discount-row',
                    isBelow ? 'drow-below' : isNear ? 'drow-near' : 'drow-above'
                  ].join(' ')}
                  onClick={() => setSelectedNo(item.vehicle.no)}
                >
                  <span className="drow-rank">{rank + 1}</span>
                  <span className="drow-car">
                    <strong>{item.vehicle.brand} {item.vehicle.model}</strong>
                    <small>{item.vehicle.year} · #{item.vehicle.no}</small>
                  </span>
                  <span className="drow-num">{formatMoney(item.vehicle.inventoryPrice)}</span>
                  <span className="drow-num drow-adjusted">{formatMoney(adjustedPrice)}</span>
                  <span className="drow-num">{formatMoney(item.kavakOffer)}</span>
                  <span className={`drow-gap ${isBelow ? 'gap-below' : isNear ? 'gap-near' : 'gap-above'}`}>
                    {isBelow ? '▼ ' : '▲ '}
                    {formatMoney(Math.abs(gap))}
                    {isBelow && <small>margen bruto</small>}
                    {isNear && <small>negociar más</small>}
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        <section className="direct-market" aria-labelledby="direct-market-title">
          <div className="section-heading">
            <div>
              <span>Kavak venta directa</span>
              <h2 id="direct-market-title">Compra bajo oferta Kavak</h2>
              <p>
                Mercado actual contra la oferta que nos da Kavak. Solo venta directa y precio publicado.
              </p>
            </div>
            <div className="scan-summary direct-summary">
              <strong>{belowPublished.length}</strong>
              <span>abajo publicados</span>
              <small>{belowDirectSale.length} confirmado, {needsExactQuote.length} por cotizar, {nearDirectSale.length} cerca, {blockedKavakInventory.length} bloqueados Kavak, {rejectedMarketTargets.length} descartados</small>
            </div>
          </div>

          <div className="direct-market-callout">
            <AlertTriangle size={18} />
            <div>
              <strong>
                {marketTargetBest
                  ? `${marketTargetBest.title}: ${marketTargetDeltaLabel(marketTargetBest)}`
                  : 'Sin compras externas abajo de Kavak'}
              </strong>
              <span>
                El contador excluye vendedor Kavak. Los casos con mas kilometraje o version dudosa no son margen confirmado hasta cotizar esa unidad exacta.
              </span>
            </div>
          </div>

          <div className="direct-market-grid">
            {directSaleMarketTargets.map((target) => (
              <article className={`direct-card direct-card-${target.status}`} key={target.id}>
                <div className="deal-topline">
                  <span className="deal-rank">#{target.priority}</span>
                  <span className={`target-badge target-badge-${target.status}`}>
                    {marketTargetStatusLabel(target)}
                  </span>
                </div>
                <h3>{target.title}</h3>
                <p className="deal-version">{target.subtitle}</p>

                <div className="direct-price-grid">
                  <div>
                    <span>Compra publicada</span>
                    <strong>{formatMoney(target.candidatePrice)}</strong>
                    <small>{formatKm(target.candidateKm)} - {target.city}</small>
                  </div>
                  <div>
                    <span>Kavak venta</span>
                    <strong>{formatMoney(target.kavakSellOffer)}</strong>
                    {target.secondaryKavakSellOffer && <small>2a oferta {formatMoney(target.secondaryKavakSellOffer)}</small>}
                  </div>
                </div>

                <div className={target.deltaToKavak >= 0 ? 'direct-delta positive' : 'direct-delta'}>
                  <strong>{marketTargetDeltaLabel(target)}</strong>
                  <span>{marketTargetFitLabel(target.fit)}</span>
                </div>

                <p className="deal-why">{target.action}</p>
                <p className="direct-evidence">{target.evidence}</p>

                <div className="direct-meta">
                  <span>{target.source}</span>
                  <span>{target.sellerName}</span>
                  <span>{target.region}</span>
                  <span>{target.observedAt}</span>
                </div>

                <a className="deal-link" href={target.sourceUrl} target="_blank" rel="noreferrer">
                  Abrir evidencia
                  <ExternalLink size={15} />
                </a>
              </article>
            ))}
          </div>
        </section>

        <section className="external-bargains" aria-labelledby="external-bargains-title">
          <div className="section-heading">
            <div>
              <span>Fuera de tu lista</span>
              <h2 id="external-bargains-title">Gangas externas muy fuertes</h2>
              <p>
                Barrido Seminuevos: CDMX, Edomex, Queretaro, Hidalgo, Puebla y Morelos. Michoacan fuera.
              </p>
            </div>
            <div className="scan-summary">
              <strong>{externalBargains.length}</strong>
              <span>candidatas</span>
              <small>{externalSaleQuotes.length} con venta Kavak; {externalAboveList.length} arriba de lista</small>
            </div>
          </div>

          <div className="external-kavak-summary">
            <span>Kavak venta directa</span>
            <strong>
              {externalAboveList.length
                ? `${externalAboveList.length} arriba de lista`
                : 'Ninguna arriba de lista'}
            </strong>
            <small>
              {externalClosestSale
                ? `Mas cerca: ${externalClosestSale.year} ${externalClosestSale.name} (${externalKavakDetail(externalKavakById.get(externalClosestSale.id), externalClosestSale.price)})`
                : `${formatMoney(externalGapTotal)} abajo de medianas`}
            </small>
          </div>

          <div className="external-grid">
            {externalBargains.map((deal) => {
              const quote = externalKavakById.get(deal.id);
              const saleDelta = quote?.sellOffer != null ? quote.sellOffer - deal.price : null;
              return (
                <article className={deal.rank === 1 ? 'external-card priority' : 'external-card'} key={deal.id}>
                  <div className="deal-topline">
                    <span className="deal-rank">#{deal.rank}</span>
                    <span className="tone-badge tone-badge-ganga">Ganga externa</span>
                  </div>
                  <h3>{deal.year} {deal.name}</h3>
                  {deal.version && <p className="deal-version">{deal.version}</p>}
                  <div className="deal-price">
                    <span>Precio publicado</span>
                    <strong>{formatMoney(deal.price)}</strong>
                  </div>
                  <div className={saleDelta != null && saleDelta >= 0 ? 'kavak-sale positive' : 'kavak-sale'}>
                    <span>Kavak venta directa</span>
                    <strong>{externalKavakDisplay(quote)}</strong>
                    <small>{externalKavakDetail(quote, deal.price)}</small>
                  </div>
                  <div className="deal-metrics">
                    <span>
                      <strong>{formatMoney(deal.gapToMedian)}</strong>
                      abajo mediana
                    </span>
                    <span>
                      <strong>{Math.round(deal.gapPct * 100)}%</strong>
                      descuento vs mediana
                    </span>
                    <span>
                      <strong>{deal.compCount}</strong>
                      comparables
                    </span>
                  </div>
                  <p className="deal-location">
                    {deal.city}, {deal.region} - {formatKm(deal.km)} - visto {deal.observedAt}
                  </p>
                  <p className="deal-why">{deal.why}</p>
                  <a className="deal-link" href={deal.url} target="_blank" rel="noreferrer">
                    Abrir ficha {deal.source}
                    <ExternalLink size={15} />
                  </a>
                </article>
              );
            })}
          </div>
          {externalTop && (
            <p className="external-footnote">
              Prioridad actual: {externalTop.year} {externalTop.name} en {externalTop.city}, {externalTop.region}, por {formatMoney(externalTop.price)}.
            </p>
          )}
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
                      {item.score > 0 && (
                        <small>
                          <span className={`score-badge${item.score >= 300 ? ' strong' : item.score >= 80 ? ' medium' : ''}`}>
                            {item.score}
                          </span>
                        </small>
                      )}
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
                {selected.score > 0 && (
                  <span className={`score-badge${selected.score >= 300 ? ' strong' : selected.score >= 80 ? ' medium' : ''}`} style={{ marginTop: 4 }}>
                    score {selected.score}
                  </span>
                )}
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
              {selected.marketReference != null && (
                <div>
                  <span>Ref. scoring (mid)</span>
                  <strong>{formatMoney(selected.marketReference)}</strong>
                </div>
              )}
              {selected.marketPriceRange != null && (
                <>
                  <div>
                    <span>Mercado alto</span>
                    <strong>{formatMoney(selected.marketPriceRange.high)}</strong>
                  </div>
                  <div>
                    <span>Mercado bajo</span>
                    <strong>{formatMoney(selected.marketPriceRange.low)}</strong>
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
              <span>Confianza {confidenceLabel(selected.confidence)} — {Math.round(selected.confidence * 100)}%</span>
              <div>
                {Array.from({ length: 10 }, (_, i) => {
                  const filled = i < Math.round(selected.confidence * 10);
                  const cls = filled
                    ? (selected.confidence >= 0.9 ? 'seg-blue' : 'seg-amber')
                    : '';
                  return <i key={i} className={cls} />;
                })}
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

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

function App() {
  const [selectedNo, setSelectedNo] = useState(opportunities[0]?.vehicle.no ?? 0);
  const [query, setQuery] = useState('');
  const [onlyPositive, setOnlyPositive] = useState(false);

  const summary = summarizeInventory(inventoryData);
  const selected = opportunities.find((item) => item.vehicle.no === selectedNo) ?? opportunities[0];
  const filtered = useMemo(() => {
    const text = query.trim().toLowerCase();
    return opportunities.filter((item) => {
      const vehicle = item.vehicle;
      const matchesText = `${vehicle.brand} ${vehicle.model} ${vehicle.year}`.toLowerCase().includes(text);
      const matchesSpread = !onlyPositive || (item.spread ?? 0) > 0;
      return matchesText && matchesSpread;
    });
  }, [query, onlyPositive]);

  const capturedRefs = opportunities.filter((item) => item.marketReference != null || item.kavakOffer != null).length;
  const positive = opportunities.filter((item) => (item.spread ?? 0) > 0);
  const publishedMargin = positive.reduce((sum, item) => sum + (item.spread ?? 0), 0);

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
            <p>Solo se rankea con Kavak capturado o publicaciones reales de mercado.</p>
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
          <div className="kpi">
            <span>Analizables</span>
            <strong>{summary.analyzable}</strong>
            <small>{summary.total} total, {summary.excludedOrange} naranjas fuera</small>
          </div>
          <div className="kpi">
            <span>Referencias reales</span>
            <strong>{capturedRefs}</strong>
            <small>Facebook, MercadoLibre, Kavak u otra URL verificable</small>
          </div>
          <div className="kpi">
            <span>Spread positivo</span>
            <strong>{positive.length}</strong>
            <small>Solo con precio real visible</small>
          </div>
          <div className="kpi accent">
            <span>Margen potencial</span>
            <strong>{formatMoney(publishedMargin)}</strong>
            <small>Contra compra objetivo -50k</small>
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
                <span>Precio real</span>
                <span>Spread</span>
              </div>
              {filtered.map((item) => (
                <button
                  className={item.vehicle.no === selected.vehicle.no ? 'table-row selected' : 'table-row'}
                  key={item.vehicle.no}
                  onClick={() => setSelectedNo(item.vehicle.no)}
                >
                  <span>
                    <strong>{item.vehicle.brand} {item.vehicle.model}</strong>
                    <small>{item.vehicle.year} · {formatKm(item.vehicle.kilometers)}</small>
                  </span>
                  <span>{formatMoney(item.vehicle.inventoryPrice)}</span>
                  <span>
                    <strong>{formatMoney(item.targetBuyPrice)}</strong>
                    <small>agresivo {formatMoney(item.aggressiveBuyPrice)}</small>
                  </span>
                  <span>
                    <strong>{formatMoney(item.marketReference ?? item.kavakOffer)}</strong>
                    <small>Kavak {statusLabel(item.kavakStatus)}</small>
                  </span>
                  <span className={(item.spread ?? 0) > 0 ? 'spread good' : 'spread muted'}>
                    {formatMoney(item.spread)}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <aside className="detail-panel">
            <div className="detail-title">
              <CircleDot size={18} />
              <div>
                <h2>{selected.vehicle.brand} {selected.vehicle.model}</h2>
                <p>{selected.vehicle.year} · {formatKm(selected.vehicle.kilometers)} · #{selected.vehicle.no}</p>
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
              <div>
                <span>Spread objetivo</span>
                <strong className={(selected.spread ?? 0) > 0 ? 'good-text' : ''}>{formatMoney(selected.spread)}</strong>
              </div>
            </div>

            <div className="confidence">
              <span>Confianza {confidenceLabel(selected.confidence)}</span>
              <div>
                <i style={{ width: `${Math.round(selected.confidence * 100)}%` }} />
              </div>
            </div>

            <section className="detail-section">
              <h3>Evidencia</h3>
              {selected.evidence.slice(0, 5).map((evidence) => (
                <a href={evidence.url} key={`${evidence.source}-${evidence.label}`} target="_blank" rel="noreferrer">
                  <span>
                    <strong>{evidence.label}</strong>
                    <small>{evidence.source} · {evidence.zone} · {evidence.status}</small>
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

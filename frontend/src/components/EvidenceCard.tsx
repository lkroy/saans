import { useState } from 'react';
import type { Evidence } from '../lib/api';
import { fmtHour } from '../lib/utils';

/** "Why this decision?" — the shared decision object, rendered the same
 *  way on the dashboard, bulletin and (as text) in Ask Saans answers. */
export default function EvidenceCard({ evidence }: { evidence: Evidence }) {
  const [open, setOpen] = useState(false);
  const conc = Object.entries(evidence.pollutant_concentrations || {});
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between text-left"
        aria-expanded={open}
      >
        <h3 className="text-sm font-bold uppercase tracking-widest text-slate-500">
          Why this decision?
        </h3>
        <span className="text-lg text-slate-400" aria-hidden>{open ? '▾' : '▸'}</span>
      </button>
      <p className="mt-2 text-sm text-slate-700">
        Reference AQI <span className="font-extrabold text-ink">{evidence.reference_aqi}</span>
        {' '}= max(current {evidence.current_aqi}, 6-hour peak {evidence.forecast_peak_6h.aqi}
        {' '}around {fmtHour(evidence.forecast_peak_6h.at)}).
      </p>
      {open && (
        <div className="mt-3 space-y-3 text-sm text-slate-700">
          <p><span className="font-semibold text-ink">Rule: </span>{evidence.rule}</p>
          <div>
            <p className="font-semibold text-ink">Current-hour pollutants (modelled, µg/m³):</p>
            <div className="mt-1 flex flex-wrap gap-2">
              {conc.map(([p, v]) => (
                <span key={p} className="rounded-lg bg-slate-100 px-2.5 py-1 font-mono text-xs">
                  {p}: {typeof v === 'number' ? v.toFixed(1) : v}
                  {p === evidence.dominant_pollutant && ' ★'}
                </span>
              ))}
            </div>
            <p className="mt-1 text-xs text-slate-500">★ dominant pollutant driving the AQI</p>
          </div>
          <p>
            <span className="font-semibold text-ink">Source: </span>{evidence.source}
            {' '}· {evidence.data_status === 'demo' ? 'scripted demo data' : 'indicative hourly estimate, not an official CPCB 24-hour value'}
            {' '}· data {evidence.data_age_min} min old
            {evidence.stale && <span className="font-semibold text-amber-700"> (stale)</span>}
          </p>
          <div>
            <p className="font-semibold text-ink">Limitations:</p>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-slate-600">
              {evidence.limitations.map((l, i) => <li key={i}>{l}</li>)}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}

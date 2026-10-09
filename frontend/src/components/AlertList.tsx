import type { AlertItem } from '../lib/api';
import { fmtDateTime } from '../lib/utils';

export default function AlertList({ alerts }: { alerts: AlertItem[] }) {
  if (alerts.length === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-bold uppercase tracking-widest text-slate-500">Active alerts</h3>
        <p className="mt-2 text-sm text-slate-600">No threshold alerts right now. We'll flag it here if air quality crosses a risk level.</p>
      </section>
    );
  }
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-bold uppercase tracking-widest text-slate-500">Active alerts</h3>
      <ul className="mt-3 space-y-3">
        {alerts.map((a, i) => (
          <li
            key={i}
            className={`rounded-xl border-l-4 p-3.5 ${
              a.severity === 'critical' ? 'border-aqi-severe bg-red-50' : 'border-aqi-moderate bg-amber-50'
            }`}
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="text-sm font-bold text-ink">{a.title}</p>
              <span className="text-xs text-slate-500">{fmtDateTime(a.at)}</span>
            </div>
            <p className="mt-1 text-sm text-slate-700">{a.detail}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

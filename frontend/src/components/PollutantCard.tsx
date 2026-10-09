import { POLLUTANT_META } from '../lib/utils';
import type { PollutantMap } from '../lib/api';

export default function PollutantCard({
  pollutant,
  value,
  dominant,
}: {
  pollutant: keyof PollutantMap;
  value: number;
  dominant: keyof PollutantMap;
}) {
  const meta = POLLUTANT_META[pollutant];
  const isDominant = pollutant === dominant;
  return (
    <div
      className={`relative rounded-2xl border bg-white p-4 shadow-sm transition hover:shadow-md ${
        isDominant ? 'border-ink ring-1 ring-ink' : 'border-slate-200'
      }`}
    >
      {isDominant && (
        <span className="absolute -top-2.5 left-3 rounded-full bg-ink px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-white">
          Dominant
        </span>
      )}
      <p className="text-sm font-bold text-ink">{meta.label}</p>
      <p className="mt-1 text-2xl font-extrabold tracking-tight text-ink">
        {value >= 100 ? Math.round(value) : value.toFixed(1)}
        <span className="ml-1 text-xs font-medium text-slate-500">{meta.unit}</span>
      </p>
      <p className="mt-1.5 text-xs leading-relaxed text-slate-500">{meta.blurb}</p>
    </div>
  );
}

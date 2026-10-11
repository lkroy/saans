import type { BestWindow } from '../lib/api';
import { categoryColor, fmtWindow, textOn } from '../lib/utils';
import type { Category } from '../lib/api';

function windowCategory(aqi: number): Category {
  if (aqi <= 50) return 'Good';
  if (aqi <= 100) return 'Satisfactory';
  if (aqi <= 200) return 'Moderate';
  if (aqi <= 300) return 'Poor';
  if (aqi <= 400) return 'Very Poor';
  return 'Severe';
}

export default function BestWindows({ windows, note }: { windows: BestWindow[]; note?: string | null }) {
  if (windows.length === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-bold uppercase tracking-widest text-slate-500">Best outdoor windows</h3>
        <p className="mt-2 text-sm text-slate-600">
          {note ?? 'No suitable outdoor window during school hours — plan outdoor activities indoors today.'}
        </p>
      </section>
    );
  }
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-bold uppercase tracking-widest text-slate-500">Best outdoor windows</h3>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {windows.map((w, i) => {
          const cat = windowCategory(w.aqi);
          const color = categoryColor(cat);
          return (
            <div key={i} className="flex items-center gap-4 rounded-xl bg-slate-50 p-4">
              <span
                className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-sm font-extrabold"
                style={{ backgroundColor: color, color: textOn(color) }}
              >
                {w.aqi}
              </span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{w.label}</p>
                <p className="text-base font-bold text-ink">{fmtWindow(w.start, w.end)}</p>
                <p className="text-xs text-slate-500">
                  AQI ~{w.aqi} · {cat}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

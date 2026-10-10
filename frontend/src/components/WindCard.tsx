import type { WindStory } from '../lib/api';

/** "Why is the air like this?" — wind-driven plain-language explanation. */
export default function WindCard({ wind }: { wind: WindStory | null }) {
  if (!wind) return null;
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start gap-4">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-sky-50">
          <svg
            width="30"
            height="30"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#0284c7"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ transform: `rotate(${wind.degrees + 180}deg)` }}
            aria-label={`Wind from ${wind.direction_label}`}
          >
            {/* arrow pointing in the direction the wind blows TOWARD */}
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5 12 12 5 19 12" />
          </svg>
        </div>
        <div>
          <h3 className="text-sm font-bold uppercase tracking-widest text-slate-500">
            Why is the air like this?
          </h3>
          <p className="mt-1 font-extrabold text-ink">{wind.headline}</p>
          <p className="mt-1 text-sm text-slate-600">{wind.detail}</p>
          <p className="mt-2 text-xs text-slate-400">
            Wind {wind.direction} ({wind.direction_label}) · {wind.speed_kmh} km/h · Open-Meteo
          </p>
        </div>
      </div>
    </section>
  );
}

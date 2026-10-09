import type { AdvisoryCall, CallLevel } from '../lib/api';

const LEVEL_STYLE: Record<CallLevel, { bg: string; border: string; badge: string; badgeText: string; icon: string }> = {
  clear: {
    bg: 'bg-green-50',
    border: 'border-aqi-good',
    badge: 'bg-aqi-good',
    badgeText: 'text-white',
    icon: '✓',
  },
  caution: {
    bg: 'bg-amber-50',
    border: 'border-aqi-moderate',
    badge: 'bg-aqi-moderate',
    badgeText: 'text-ink',
    icon: '!',
  },
  indoor: {
    bg: 'bg-orange-50',
    border: 'border-aqi-poor',
    badge: 'bg-aqi-poor',
    badgeText: 'text-white',
    icon: '⌂',
  },
  severe: {
    bg: 'bg-red-50',
    border: 'border-aqi-severe',
    badge: 'bg-aqi-severe',
    badgeText: 'text-white',
    icon: '⚠',
  },
};

const LEVEL_LABEL: Record<CallLevel, string> = {
  clear: 'All clear',
  caution: 'Caution',
  indoor: 'Indoor day',
  severe: 'Severe',
};

export default function AdvisoryBanner({ call }: { call: AdvisoryCall }) {
  const s = LEVEL_STYLE[call.level];
  return (
    <section className={`rounded-2xl border-l-8 ${s.border} ${s.bg} p-5 shadow-sm`} aria-live="polite">
      <div className="flex flex-wrap items-center gap-3">
        <span className={`flex h-9 w-9 items-center justify-center rounded-full text-lg font-bold ${s.badge} ${s.badgeText}`} aria-hidden>
          {s.icon}
        </span>
        <div>
          <p className={`text-xs font-bold uppercase tracking-widest ${s.badgeText === 'text-white' ? 'text-slate-600' : 'text-slate-600'}`}>
            Today's call · {LEVEL_LABEL[call.level]}
          </p>
          <h2 className="text-xl font-extrabold text-ink sm:text-2xl">{call.headline}</h2>
        </div>
      </div>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-700">{call.detail}</p>
    </section>
  );
}

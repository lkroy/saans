import { useCallback, useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api, type AdvisoryResponse, type CurrentAqi, type ForecastResponse, type PollutantMap } from '../lib/api';
import { useLocation } from '../lib/location';
import { categoryColor, fmtDateTime, fmtHour, textOn } from '../lib/utils';
import CitySearch from '../components/CitySearch';
import AQIGauge from '../components/AQIGauge';
import PollutantCard from '../components/PollutantCard';
import AdvisoryBanner from '../components/AdvisoryBanner';
import WindCard from '../components/WindCard';
import BestWindows from '../components/BestWindows';
import AlertList from '../components/AlertList';
import { DashboardSkeleton, ErrorState } from '../components/Feedback';

const POLLUTANT_ORDER: (keyof PollutantMap)[] = ['pm2_5', 'pm10', 'o3', 'no2', 'so2', 'co'];

function ChartTooltip({ active, payload }: { active?: boolean; payload?: { payload: ForecastPoint }[] }) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0].payload;
  const color = categoryColor(p.category);
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs shadow-lg">
      <p className="font-semibold text-slate-500">{p.fullLabel}</p>
      <p className="mt-1 flex items-center gap-1.5 text-sm font-extrabold text-ink">
        <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
        AQI {p.aqi} · {p.category}
      </p>
      <p className="mt-0.5 text-slate-500">
        PM2.5 {p.pm2_5.toFixed(1)} · PM10 {p.pm10.toFixed(1)} µg/m³
      </p>
    </div>
  );
}

interface ForecastPoint {
  time: string;
  aqi: number;
  category: Parameters<typeof categoryColor>[0];
  pm2_5: number;
  pm10: number;
  label: string;
  fullLabel: string;
  fill: string;
  cy: number;
}

function ForecastChart({ data }: { data: ForecastResponse }) {
  const points: ForecastPoint[] = data.hours.map((h) => ({
    ...h,
    label: fmtHour(h.time),
    fullLabel: fmtDateTime(h.time),
    fill: categoryColor(h.category),
    cy: 0.5,
  }));

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-bold uppercase tracking-widest text-slate-500">48-hour AQI forecast</h3>
        <span className="flex flex-wrap gap-2 text-[11px] text-slate-500">
          {(Object.keys({ Good: 1, Satisfactory: 1, Moderate: 1, Poor: 1, 'Very Poor': 1, Severe: 1 }) as ForecastPoint['category'][]).map(
            (c) => (
              <span key={c} className="flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: categoryColor(c) }} />
                {c}
              </span>
            ),
          )}
        </span>
      </div>
      <div className="mt-3 h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
            <defs>
              <linearGradient id="aqiFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#1a2b3c" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#1a2b3c" stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: '#64748b' }}
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
              interval={5}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#64748b' }}
              tickLine={false}
              axisLine={false}
              domain={[0, 'dataMax + 40']}
            />
            <Tooltip content={<ChartTooltip />} />
            <Area
              type="monotone"
              dataKey="aqi"
              stroke="#1a2b3c"
              strokeWidth={2.5}
              fill="url(#aqiFill)"
              dot={false}
              activeDot={{ r: 5, strokeWidth: 0 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {/* Category-colored dots row under the chart */}
      <div className="mt-1 h-24 w-full" aria-hidden>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 4, right: 12, bottom: 0, left: -12 }}>
            <XAxis dataKey="label" type="category" tick={false} axisLine={false} interval={5} />
            <YAxis hide domain={[0, 1]} />
            <Scatter data={points} dataKey="cy" isAnimationActive={false}>
              {points.map((p, i) => (
                <Cell key={i} fill={p.fill} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export default function Dashboard() {
  const { location } = useLocation();
  const [current, setCurrent] = useState<CurrentAqi | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [advisory, setAdvisory] = useState<AdvisoryResponse | null>(null);
  const [alerts, setAlerts] = useState<{ alerts: { severity: 'warn' | 'critical'; title: string; detail: string; at: string }[] } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  const load = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const { lat, lon } = location;
    Promise.all([api.currentAqi(lat, lon), api.forecast(lat, lon, 48), api.advisory(lat, lon), api.alerts(lat, lon)])
      .then(([c, f, a, al]) => {
        if (cancelled) return;
        setCurrent(c);
        setForecast(f);
        setAdvisory(a);
        setAlerts(al);
      })
      .catch((e) => {
        if (!cancelled) setError(e);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [location, attempt]);

  useEffect(() => load(), [load]);

  if (loading) {
    return (
      <div className="space-y-6">
        <CitySearch />
        <DashboardSkeleton />
      </div>
    );
  }

  if (error || !current || !forecast || !advisory || !alerts) {
    return (
      <div className="space-y-6">
        <CitySearch />
        <ErrorState error={error ?? new Error('No data returned.')} onRetry={() => setAttempt((n) => n + 1)} />
      </div>
    );
  }

  const domMeta = {
    pm2_5: 'PM2.5',
    pm10: 'PM10',
    o3: 'O₃',
    no2: 'NO₂',
    so2: 'SO₂',
    co: 'CO',
  } as const;

  return (
    <div className="space-y-6">
      <CitySearch />

      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">
          Air safety in {location.label.split(',')[0]}
        </h1>
        <p className="text-xs text-slate-500">Updated {fmtDateTime(current.updated_at)}</p>
      </div>

      <AdvisoryBanner call={advisory.call} />

      <WindCard wind={advisory.wind} />

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-bold uppercase tracking-widest text-slate-500">Current AQI</h3>
          <AQIGauge aqi={current.aqi} category={current.category} />
          <p className="mt-2 text-center text-sm text-slate-600">
            Dominant pollutant:{' '}
            <span className="font-bold text-ink">{domMeta[current.dominant]}</span>
          </p>
        </section>

        <div className="space-y-6 lg:col-span-2">
          <BestWindows windows={advisory.best_windows} />
          <AlertList alerts={alerts.alerts} />
        </div>
      </div>

      <section>
        <h3 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">Pollutant breakdown</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
          {POLLUTANT_ORDER.map((p) => (
            <PollutantCard key={p} pollutant={p} value={current.pollutants[p]} dominant={current.dominant} />
          ))}
        </div>
      </section>

      <ForecastChart data={forecast} />

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-4 text-sm text-slate-600 sm:grid-cols-3">
          <div>
            <p className="font-bold text-ink">AQI now</p>
            <p className="mt-1 flex items-center gap-2">
              <span
                className="inline-block rounded-full px-2.5 py-0.5 text-xs font-extrabold"
                style={{ backgroundColor: current.color, color: textOn(current.color) }}
              >
                {current.aqi}
              </span>
              {current.category}
            </p>
          </div>
          <div>
            <p className="font-bold text-ink">Peak in next 6 hours</p>
            <p className="mt-1">
              AQI <span className="font-extrabold text-ink">{advisory.peak_6h.aqi}</span> at{' '}
              {fmtHour(advisory.peak_6h.at)}
            </p>
          </div>
          <div>
            <p className="font-bold text-ink">Data source</p>
            <p className="mt-1">{current.source}</p>
          </div>
        </div>
      </section>

      <p className="text-center text-xs text-slate-400">
        Indicative hourly AQI · modelled data (Open-Meteo). CPCB officially uses 24-hour averages; treat these
        numbers as guidance, not a regulatory reading.
      </p>
    </div>
  );
}

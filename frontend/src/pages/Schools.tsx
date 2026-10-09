import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type Bulletin, type School, type SearchResult } from '../lib/api';
import { categoryColor, fmtDateLong, fmtDayHour, fmtHour, textOn } from '../lib/utils';
import { ErrorState, SkeletonCard } from '../components/Feedback';
import AdvisoryBanner from '../components/AdvisoryBanner';
import BestWindows from '../components/BestWindows';

/* ---------------- Add-school form ---------------- */

function AddSchoolForm({ onAdded }: { onAdded: (s: School) => void }) {
  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [contact, setContact] = useState('');
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const searchCity = (q: string) => {
    setCity(q);
    setCoords(null);
    if (timer.current) window.clearTimeout(timer.current);
    if (q.trim().length < 2) {
      setResults([]);
      return;
    }
    timer.current = window.setTimeout(() => {
      api
        .search(q.trim())
        .then((r) => {
          setResults(r.results);
          setOpen(true);
        })
        .catch(() => setResults([]));
    }, 350);
  };

  const pickCity = (r: SearchResult) => {
    setCity(`${r.name}, ${[r.admin1, r.country].filter(Boolean).join(', ')}`);
    setCoords({ lat: r.lat, lon: r.lon });
    setResults([]);
    setOpen(false);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError('Please enter the school name.');
      return;
    }
    if (!coords) {
      setError('Please pick a city from the search suggestions so we can pin its location.');
      return;
    }
    setSaving(true);
    try {
      const school = await api.addSchool({
        name: name.trim(),
        city: city.trim(),
        lat: coords.lat,
        lon: coords.lon,
        ...(contact.trim() ? { contact: contact.trim() } : {}),
      });
      onAdded(school);
      setName('');
      setCity('');
      setContact('');
      setCoords(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not add the school.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="no-print rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-extrabold text-ink">Add a school</h2>
      <p className="mt-1 text-sm text-slate-500">
        Register a school to get a printable morning bulletin with today's air-safety call.
      </p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">School name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Delhi Public School, Patna"
            className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-ink focus:ring-2 focus:ring-ink/10"
          />
        </label>
        <div className="relative" ref={boxRef}>
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">City</span>
            <input
              value={city}
              onChange={(e) => searchCity(e.target.value)}
              onFocus={() => results.length > 0 && setOpen(true)}
              placeholder="Start typing a city…"
              className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-ink focus:ring-2 focus:ring-ink/10"
            />
          </label>
          {coords && (
            <p className="mt-1.5 text-xs text-aqi-good">
              📍 Pinned at {coords.lat.toFixed(3)}, {coords.lon.toFixed(3)}
            </p>
          )}
          {open && results.length > 0 && (
            <ul className="absolute z-50 mt-1 max-h-56 w-full overflow-auto rounded-xl border border-slate-200 bg-white py-1 shadow-xl">
              {results.map((r, i) => (
                <li key={`${r.lat}-${r.lon}-${i}`}>
                  <button
                    type="button"
                    onClick={() => pickCity(r)}
                    className="w-full px-4 py-2.5 text-left text-sm hover:bg-slate-50"
                  >
                    <span className="font-medium text-ink">{r.name}</span>{' '}
                    <span className="text-slate-500">{[r.admin1, r.country].filter(Boolean).join(', ')}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <label className="block sm:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Contact <span className="font-normal normal-case">(optional)</span>
          </span>
          <input
            value={contact}
            onChange={(e) => setContact(e.target.value)}
            placeholder="e.g. principal@example.org"
            className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-ink focus:ring-2 focus:ring-ink/10"
          />
        </label>
      </div>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={saving}
        className="mt-4 rounded-xl bg-ink px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
      >
        {saving ? 'Adding…' : 'Add school'}
      </button>
    </form>
  );
}

/* ---------------- Bulletin view (printable) ---------------- */

function BulletinView({ school, onBack }: { school: School; onBack: () => void }) {
  const [bulletin, setBulletin] = useState<Bulletin | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .bulletin(school.id)
      .then((b) => {
        if (!cancelled) setBulletin(b);
      })
      .catch((e) => {
        if (!cancelled) setError(e);
      });
    return () => {
      cancelled = true;
    };
  }, [school.id]);

  const color = bulletin ? categoryColor(bulletin.category) : '#64748b';

  return (
    <div className="space-y-6">
      <div className="no-print flex flex-wrap items-center gap-3">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
        >
          ← All schools
        </button>
        {bulletin && (
          <button
            onClick={() => window.print()}
            className="flex items-center gap-1.5 rounded-xl bg-ink px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v8H6z" />
            </svg>
            Print bulletin
          </button>
        )}
      </div>

      {!bulletin && !error && (
        <div className="space-y-4">
          <SkeletonCard className="h-32" />
          <SkeletonCard className="h-64" />
        </div>
      )}
      {error ? <ErrorState error={error} /> : null}

      {bulletin && (
        <article className="print-card rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500">
                Saans · Morning air-safety bulletin
              </p>
              <h1 className="mt-1 text-2xl font-extrabold text-ink">{bulletin.school.name}</h1>
              <p className="text-sm text-slate-500">
                {bulletin.school.city} · {fmtDateLong(bulletin.date)}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-4xl font-extrabold text-ink">{bulletin.aqi_now}</span>
              <span
                className="rounded-full px-3.5 py-1.5 text-sm font-bold"
                style={{ backgroundColor: color, color: textOn(color) }}
              >
                {bulletin.category}
              </span>
            </div>
          </div>

          <div className="mt-5">
            <AdvisoryBanner call={bulletin.call} />
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Today's peak</p>
              <p className="mt-1 text-lg font-extrabold text-ink">
                AQI {bulletin.peak_today.aqi}{' '}
                <span className="text-sm font-medium text-slate-500">around {fmtHour(bulletin.peak_today.at)}</span>
              </p>
            </div>
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Generated</p>
              <p className="mt-1 text-sm font-medium text-slate-700">{fmtDayHour(bulletin.generated_at)}</p>
            </div>
          </div>

          <div className="mt-5">
            <BestWindows windows={bulletin.best_windows} />
          </div>

          <div className="mt-5">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-500">Today's checklist</h2>
            <ul className="mt-3 space-y-2.5">
              {bulletin.checklist.map((item, i) => (
                <li key={i} className="flex items-start gap-3 rounded-xl border border-slate-200 p-3.5">
                  <span
                    className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border-2 border-slate-300"
                    aria-hidden
                  />
                  <span className="text-sm text-slate-800">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <p className="mt-6 border-t border-slate-200 pt-4 text-xs text-slate-400">
            Indicative hourly AQI · modelled data (Open-Meteo). Post near the school office noticeboard.
          </p>
        </article>
      )}
    </div>
  );
}

/* ---------------- Schools page ---------------- */

export default function Schools() {
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [selected, setSelected] = useState<School | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .listSchools()
      .then((r) => setSchools(r.schools))
      .catch((e) => setError(e))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const remove = async (id: string) => {
    if (!window.confirm('Remove this school?')) return;
    setDeleting(id);
    try {
      await api.deleteSchool(id);
      setSchools((s) => s.filter((x) => x.id !== id));
      if (selected?.id === id) setSelected(null);
    } catch (e) {
      setError(e);
    } finally {
      setDeleting(null);
    }
  };

  if (selected) {
    return <BulletinView school={selected} onBack={() => setSelected(null)} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">Schools</h1>
        <p className="mt-1 text-sm text-slate-500">
          Register schools to generate a printable morning air-safety bulletin for each one.
        </p>
      </div>

      <AddSchoolForm onAdded={(s) => setSchools((prev) => [s, ...prev])} />

      <section>
        <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
          Registered schools ({schools.length})
        </h2>
        {loading && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <SkeletonCard key={i} className="h-36" />
            ))}
          </div>
        )}
        {error ? <ErrorState error={error} onRetry={load} /> : null}
        {!loading && !error && schools.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
            <p className="text-sm font-semibold text-slate-600">No schools yet</p>
            <p className="mt-1 text-sm text-slate-500">
              Add your first school above — its bulletin will appear here.
            </p>
          </div>
        )}
        {!loading && !error && schools.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {schools.map((s) => (
              <div
                key={s.id}
                className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md"
              >
                <h3 className="font-extrabold text-ink">{s.name}</h3>
                <p className="mt-0.5 text-sm text-slate-500">{s.city}</p>
                <p className="mt-1 font-mono text-[11px] text-slate-400">
                  {s.lat.toFixed(3)}, {s.lon.toFixed(3)}
                </p>
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={() => setSelected(s)}
                    className="flex-1 rounded-xl bg-ink px-3 py-2 text-sm font-semibold text-white transition hover:opacity-90"
                  >
                    View bulletin
                  </button>
                  <button
                    onClick={() => remove(s.id)}
                    disabled={deleting === s.id}
                    className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50 disabled:opacity-50"
                    aria-label={`Remove ${s.name}`}
                  >
                    {deleting === s.id ? '…' : 'Remove'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

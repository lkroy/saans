import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type Bulletin, type School, type SearchResult } from '../lib/api';
import { categoryColor, fmtDateLong, fmtDayHour, fmtHour, textOn } from '../lib/utils';
import { ErrorState, SkeletonCard } from '../components/Feedback';
import AdvisoryBanner from '../components/AdvisoryBanner';
import BestWindows from '../components/BestWindows';
import EvidenceCard from '../components/EvidenceCard';

/* ---------------- Add-school form ---------------- */

function AddSchoolForm({ onAdded }: { onAdded: (s: School) => void }) {
  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [contact, setContact] = useState('');
  const [hoursStart, setHoursStart] = useState('08:00');
  const [hoursEnd, setHoursEnd] = useState('15:00');
  const [days, setDays] = useState<number[]>([0, 1, 2, 3, 4, 5]);
  const [ptDuration, setPtDuration] = useState('40');
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
        hours: { start: hoursStart, end: hoursEnd },
        days,
        pt_duration_min: Math.max(15, Math.min(180, parseInt(ptDuration, 10) || 40)),
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
        <div className="grid gap-4 sm:col-span-2 sm:grid-cols-3">
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">School hours (IST)</span>
            <div className="mt-1.5 flex items-center gap-2">
              <input type="time" value={hoursStart} onChange={(e) => setHoursStart(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-ink" />
              <span className="text-slate-400">–</span>
              <input type="time" value={hoursEnd} onChange={(e) => setHoursEnd(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-ink" />
            </div>
          </label>
          <div>
            <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">School days</span>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((d, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setDays((prev) => prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i].sort())}
                  className={`flex h-9 w-9 items-center justify-center rounded-lg text-xs font-bold ${days.includes(i) ? 'bg-ink text-white' : 'border border-slate-300 text-slate-600'}`}
                  aria-pressed={days.includes(i)}
                  title={['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][i]}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">Typical PT duration (min)</span>
            <input
              type="number" min={15} max={180} value={ptDuration}
              onChange={(e) => setPtDuration(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-ink focus:ring-2 focus:ring-ink/10"
            />
          </label>
        </div>
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
  const [lang, setLang] = useState<'en' | 'hi'>('en');
  const [copied, setCopied] = useState(false);
  const [checked, setChecked] = useState<number[]>([]);

  // Persist checklist ticks per school per day (principal's own tracking).
  useEffect(() => {
    if (!bulletin) return;
    try {
      const raw = localStorage.getItem(`saans-checklist:${school.id}:${bulletin.date}`);
      setChecked(raw ? JSON.parse(raw) : []);
    } catch {
      setChecked([]);
    }
  }, [school.id, bulletin?.date]);

  const toggleCheck = (i: number) => {
    if (!bulletin) return;
    setChecked((prev) => {
      const next = prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i];
      try {
        localStorage.setItem(`saans-checklist:${school.id}:${bulletin.date}`, JSON.stringify(next));
      } catch { /* storage unavailable */ }
      return next;
    });
  };

  useEffect(() => {
    let cancelled = false;
    setBulletin(null);
    setError(null);
    api
      .bulletin(school.id, lang)
      .then((b) => {
        if (!cancelled) setBulletin(b);
      })
      .catch((e) => {
        if (!cancelled) setError(e);
      });
    return () => {
      cancelled = true;
    };
  }, [school.id, lang]);

  const color = bulletin ? categoryColor(bulletin.category) : '#64748b';
  const s = bulletin?.strings;

  const bulletinText = () => {
    if (!bulletin) return '';
    const lines = [
      `${s?.bulletin_title ?? 'Saans · Morning air-safety bulletin'} — ${bulletin.school.name}`,
      `${bulletin.school.city} · ${bulletin.date}`,
      '',
      `${bulletin.call.label ?? ''}: ${bulletin.call.headline}`,
      `AQI now: ${bulletin.aqi_now} (${bulletin.category})`,
      bulletin.activity_plan ? `Plan: ${bulletin.activity_plan.reason}` : '',
      '',
      ...(bulletin.checklist.map((c, i) => `${i + 1}. ${c}`)),
      '',
      bulletin.disclaimer,
    ];
    return lines.filter(Boolean).join('\n');
  };

  const copyBulletin = async () => {
    try {
      await navigator.clipboard.writeText(bulletinText());
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable */
    }
  };

  const shareBulletin = async () => {
    const text = bulletinText();
    if (navigator.share) {
      try {
        await navigator.share({ title: `Saans bulletin — ${bulletin?.school.name}`, text });
      } catch { /* dismissed */ }
    } else {
      copyBulletin();
    }
  };

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
          <>
            <div className="flex rounded-xl border border-slate-300 bg-white p-0.5 text-sm font-semibold shadow-sm">
              {(['en', 'hi'] as const).map((l) => (
                <button
                  key={l}
                  onClick={() => setLang(l)}
                  className={`rounded-lg px-3 py-1.5 ${lang === l ? 'bg-ink text-white' : 'text-slate-600'}`}
                >
                  {l === 'en' ? 'English' : 'हिंदी'}
                </button>
              ))}
            </div>
            <button
              onClick={copyBulletin}
              className="flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
            >
              {copied ? 'Copied ✓' : 'Copy text'}
            </button>
            <button
              onClick={shareBulletin}
              className="flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
            >
              Share
            </button>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-1.5 rounded-xl bg-ink px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v8H6z" />
              </svg>
              Print bulletin
            </button>
          </>
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
                {s?.bulletin_title ?? 'Saans · Morning air-safety bulletin'}
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
          <p className="mt-2 text-[11px] font-bold text-slate-500">
            <span className="rounded-full bg-slate-100 px-2.5 py-1">Indicative · modelled</span>{' '}
            <span className="font-normal">hourly estimate, not an official CPCB 24-hour value</span>
          </p>

          <div className="mt-5">
            <AdvisoryBanner call={bulletin.call} />
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500">{s?.todays_peak ?? "Today's peak"}</p>
              <p className="mt-1 text-lg font-extrabold text-ink">
                AQI {bulletin.peak_today.aqi}{' '}
                <span className="text-sm font-medium text-slate-500">around {fmtHour(bulletin.peak_today.at)}</span>
              </p>
            </div>
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500">{s?.generated ?? 'Generated'}</p>
              <p className="mt-1 text-sm font-medium text-slate-700">{fmtDayHour(bulletin.generated_at)}</p>
            </div>
          </div>

          {bulletin.activity_plan && (
            <div className="mt-5 rounded-xl border border-sky-200 bg-sky-50 p-4">
              <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Activity plan · {bulletin.activity_plan.activity}</p>
              <p className="mt-1.5 text-sm font-semibold text-ink">
                {bulletin.activity_plan.recommendation === 'outdoor_slot' && bulletin.activity_plan.slot
                  ? `Outdoors ${fmtHour(bulletin.activity_plan.slot.start)}–${fmtHour(bulletin.activity_plan.slot.end)}`
                  : 'Hold indoors'}
              </p>
              <p className="mt-1 text-sm text-slate-700">{bulletin.activity_plan.reason}</p>
            </div>
          )}

          <div className="mt-5">
            <BestWindows windows={bulletin.best_windows} note={bulletin.windows_note} />
          </div>

          <div className="mt-5">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-500">{s?.checklist_title ?? "Today's checklist"}</h2>
            <ul className="mt-3 space-y-2.5">
              {bulletin.checklist.map((item, i) => {
                const done = checked.includes(i);
                return (
                  <li key={i}>
                    <button
                      onClick={() => toggleCheck(i)}
                      aria-pressed={done}
                      className={`flex w-full items-start gap-3 rounded-xl border p-3.5 text-left transition ${
                        done ? 'border-emerald-300 bg-emerald-50' : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <span
                        className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border-2 text-sm font-extrabold ${
                          done ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-slate-300 text-transparent'
                        }`}
                        aria-hidden
                      >
                        ✓
                      </span>
                      <span className={`text-sm ${done ? 'text-slate-500 line-through' : 'text-slate-800'}`}>{item}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>

          <p className="mt-6 border-t border-slate-200 pt-4 text-xs leading-relaxed text-slate-500">
            {bulletin.disclaimer}
          </p>
          <p className="mt-2 text-xs text-slate-400">
            {s?.indicative_note ?? 'Indicative hourly AQI · modelled data (Open-Meteo). Post near the school office noticeboard.'}
          </p>
        </article>
      )}

      {bulletin?.evidence && (
        <EvidenceCard evidence={bulletin.evidence} />
      )}

      {bulletin && <ActionLogPanel schoolId={school.id} />}

      {bulletin && <PlannerPanel schoolId={school.id} />}

      {bulletin && <SubscribePanel schoolId={school.id} />}
    </div>
  );
}

/* ---------------- Teacher acknowledgement + action log ---------------- */

const ACTION_KEYS = [
  'guidance_reviewed',
  'pt_moved_indoors',
  'assembly_rescheduled',
  'outdoor_rescheduled',
  'unable_to_implement',
] as const;

function ActionLogPanel({ schoolId }: { schoolId: string }) {
  const [actions, setActions] = useState<import('../lib/api').ActionRecord[]>([]);
  const [types, setTypes] = useState<Record<string, string>>({});
  const [name, setName] = useState('');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const today = new Date().toISOString().slice(0, 10);

  const load = useCallback(() => {
    api
      .actionHistory(schoolId, today)
      .then((r) => {
        setActions(r.actions);
        setTypes(r.action_types);
      })
      .catch(() => {});
  }, [schoolId, today]);

  useEffect(() => {
    load();
  }, [load]);

  const doneToday = new Set(actions.map((a) => a.action));

  const record = async (action: string) => {
    if (!name.trim()) {
      setMsg('Please enter your name so the log shows who acknowledged.');
      return;
    }
    setBusy(action);
    setMsg(null);
    try {
      const r = await api.recordAction(schoolId, action, name.trim(), reason.trim() || undefined);
      if (r.created) {
        setMsg(`Recorded: ${r.action.label}.`);
      } else {
        setMsg('Already recorded today — no duplicate entry created.');
      }
      setReason('');
      load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Could not record the action.');
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="no-print rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-sm font-bold uppercase tracking-widest text-slate-500">
        Teacher acknowledgement · today
      </h2>
      <p className="mt-1 text-sm text-slate-600">
        Record what the school did with today's guidance. One entry per action per day.
      </p>

      <label className="mt-4 block max-w-xs">
        <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">Your name</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Meera Sharma"
          className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-ink"
        />
      </label>

      <div className="mt-4 flex flex-wrap gap-2">
        {ACTION_KEYS.map((k) => (
          <button
            key={k}
            onClick={() => record(k)}
            disabled={busy !== null || doneToday.has(k)}
            className={`rounded-xl px-4 py-2 text-sm font-semibold ${
              doneToday.has(k)
                ? 'bg-emerald-100 text-emerald-800'
                : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50'
            }`}
          >
            {doneToday.has(k) ? '✓ ' : ''}
            {types[k] ?? k}
            {busy === k ? '…' : ''}
          </button>
        ))}
      </div>

      {ACTION_KEYS.includes('unable_to_implement') && (
        <label className="mt-3 block max-w-md">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Reason <span className="font-normal normal-case">(for "Unable to implement", optional)</span>
          </span>
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. no indoor hall available"
            className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-ink"
          />
        </label>
      )}

      {msg && <p className="mt-3 text-sm text-slate-700">{msg}</p>}

      {actions.length > 0 && (
        <div className="mt-5">
          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500">Today's log</h3>
          <ul className="mt-2 space-y-1.5">
            {actions.map((a, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2 text-sm text-slate-700">
                <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-800">✓</span>
                <span className="font-semibold text-ink">{a.label}</span>
                <span className="text-slate-500">by {a.recorded_by}</span>
                {a.reason && <span className="text-slate-500">— {a.reason}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

/* ---------------- Activity planner ---------------- */

function PlannerPanel({ schoolId }: { schoolId: string }) {
  const [activity, setActivity] = useState('PT');
  const [duration, setDuration] = useState('40');
  const [preferred, setPreferred] = useState<'any' | 'morning' | 'afternoon'>('any');
  const [plan, setPlan] = useState<import('../lib/api').ActivityPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      const p = await api.planActivity(
        schoolId,
        activity.trim() || 'PT',
        Math.max(15, Math.min(180, parseInt(duration, 10) || 40)),
        preferred === 'any' ? undefined : preferred,
      );
      setPlan(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not plan the activity.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="no-print rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-sm font-bold uppercase tracking-widest text-slate-500">
        Activity planner
      </h2>
      <p className="mt-1 text-sm text-slate-600">
        Find a practical slot inside school hours — or get an indoor alternative with the reason.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">Activity</span>
          <input value={activity} onChange={(e) => setActivity(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-ink" />
        </label>
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">Duration (min)</span>
          <input type="number" min={15} max={180} value={duration} onChange={(e) => setDuration(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-ink" />
        </label>
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">Preferred</span>
          <select value={preferred} onChange={(e) => setPreferred(e.target.value as 'any' | 'morning' | 'afternoon')}
            className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-ink">
            <option value="any">Any time</option>
            <option value="morning">Morning</option>
            <option value="afternoon">Afternoon</option>
          </select>
        </label>
        <div className="flex items-end">
          <button onClick={run} disabled={busy}
            className="w-full rounded-xl bg-ink px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50">
            {busy ? 'Planning…' : 'Find a slot'}
          </button>
        </div>
      </div>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {plan && (
        <div className={`mt-4 rounded-xl p-4 ${plan.recommendation === 'outdoor_slot' ? 'bg-emerald-50 border border-emerald-200' : 'bg-amber-50 border border-amber-200'}`}>
          <p className="text-sm font-extrabold text-ink">
            {plan.recommendation === 'outdoor_slot' && plan.slot
              ? `Outdoors ${fmtHour(plan.slot.start)}–${fmtHour(plan.slot.end)} (AQI ~${plan.slot.aqi})`
              : 'Hold indoors'}
          </p>
          <p className="mt-1 text-sm text-slate-700">{plan.reason}</p>
        </div>
      )}
    </section>
  );
}

/* ---------------- SMS/email bulletin subscriptions ---------------- */

function SubscribePanel({ schoolId }: { schoolId: string }) {
  const [channel, setChannel] = useState<'sms' | 'email'>('sms');
  const [target, setTarget] = useState('');
  const [subs, setSubs] = useState<School['subscriptions']>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    api.getSchool(schoolId).then((s) => setSubs(s.subscriptions ?? [])).catch(() => {});
  }, [schoolId]);

  const submit = async () => {
    if (!target.trim() || busy) return;
    setBusy(true);
    setMsg(null);
    try {
      const r = await api.subscribe(schoolId, channel, target.trim());
      setSubs((prev) => [...(prev ?? []).filter((s) => !(s.channel === r.subscription.channel && s.target === r.subscription.target)), r.subscription]);
      setMsg({ ok: true, text: r.note });
      setTarget('');
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : 'Subscription failed. Please try again.' });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="no-print rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-sm font-bold uppercase tracking-widest text-slate-500">
        Get the 5:30 AM bulletin by text
      </h2>
      <p className="mt-1 text-sm text-slate-600">
        The principal gets this bulletin as an SMS or email every morning at 5:30 AM — no app to open.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {(['sms', 'email'] as const).map((c) => (
          <button
            key={c}
            onClick={() => { setChannel(c); setMsg(null); }}
            className={`rounded-xl px-4 py-2 text-sm font-semibold ${channel === c ? 'bg-ink text-white' : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}
          >
            {c === 'sms' ? 'SMS' : 'Email'}
          </button>
        ))}
      </div>

      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <input
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          placeholder={channel === 'sms' ? '10-digit mobile number' : 'Email address'}
          inputMode={channel === 'sms' ? 'tel' : 'email'}
          className="flex-1 rounded-xl border border-slate-300 px-4 py-2.5 text-sm shadow-sm focus:border-ink focus:outline-none"
        />
        <button
          onClick={submit}
          disabled={busy || !target.trim()}
          className="rounded-xl bg-ink px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-40"
        >
          {busy ? 'Subscribing…' : 'Subscribe'}
        </button>
      </div>

      {msg && (
        <p className={`mt-3 text-sm ${msg.ok ? 'text-emerald-700' : 'text-red-600'}`}>{msg.text}</p>
      )}

      {(subs ?? []).length > 0 && (
        <ul className="mt-4 space-y-1.5">
          {(subs ?? []).map((s, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-slate-600">
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-bold uppercase text-slate-500">{s.channel}</span>
              <span className="font-medium text-ink">{s.target}</span>
              <span className="text-xs text-slate-400">· {s.status.replace(/_/g, ' ')}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
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

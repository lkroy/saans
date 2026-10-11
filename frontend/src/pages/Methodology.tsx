import { AQI_BANDS, categoryColor } from '../lib/utils';

export default function Methodology() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">Methodology</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          How Saans turns raw air-quality data into school-day decisions — and what the numbers do and don't mean.
        </p>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-extrabold text-ink">Data sources</h2>
        <ul className="mt-3 space-y-3 text-sm leading-relaxed text-slate-700">
          <li>
            <span className="font-semibold text-ink">Current &amp; forecast air quality — Open-Meteo Air Quality API.</span>{' '}
            Free, no API key required. It blends CAMS (Copernicus Atmosphere Monitoring Service) model output and
            returns hourly pollutant concentrations for PM2.5, PM10, O₃, NO₂, SO₂ and CO. Every response from our
            backend carries <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs">source: "open-meteo (modelled)"</code>.
          </li>
          <li>
            <span className="font-semibold text-ink">City search — Open-Meteo Geocoding API.</span> Free place-name
            search, biased toward India, returning latitude/longitude used for all downstream calls.
          </li>
          <li>
            <span className="font-semibold text-ink">AQI math — CPCB (India) breakpoints.</span> The backend converts
            each pollutant's concentration into an AQI sub-index using India's Central Pollution Control Board
            breakpoint tables, and takes the maximum as the overall AQI. The dominant pollutant is the one driving
            that maximum.
          </li>
        </ul>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-extrabold text-ink">CPCB categories used across the app</h2>
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {AQI_BANDS.map((b) => (
            <div key={b.category} className="rounded-xl p-3" style={{ backgroundColor: `${categoryColor(b.category)}1a` }}>
              <p className="text-sm font-extrabold" style={{ color: categoryColor(b.category) }}>
                {b.category}
              </p>
              <p className="text-xs text-slate-600">
                AQI {b.from}–{b.to}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-extrabold text-ink">What "indicative" means</h2>
        <div className="mt-3 space-y-3 text-sm leading-relaxed text-slate-700">
          <p>
            The dashboard shows an <span className="font-semibold">indicative hourly AQI</span>: each hour's AQI is
            computed from that hour's modelled pollutant concentration. CPCB's official AQI, by contrast, is defined
            on <span className="font-semibold">24-hour averages</span> (8-hour for O₃ and CO).
          </p>
          <p>
            Hourly indicative values are more responsive — they show the morning spike when children commute and the
            afternoon dip — which is exactly what a school-day call needs. But they are not regulatory readings and
            will differ from CPCB's published daily AQI. That's why every number in Saans is labelled "indicative
            hourly AQI · modelled data (Open-Meteo)".
          </p>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-extrabold text-ink">How the school-day call is made</h2>
        <ol className="mt-3 space-y-2.5 text-sm leading-relaxed text-slate-700">
          <li className="flex gap-2.5">
            <span className="font-extrabold text-ink">1.</span>
            Take the maximum of the current AQI and the 6-hour forecast peak.
          </li>
          <li className="flex gap-2.5">
            <span className="font-extrabold text-ink">2.</span>
            Map it to a school-day call: ≤100 → <em>All clear</em>; 101–200 → <em>Caution advised</em>;
            201–300 → <em>Indoor day</em>; 301+ → <em>Emergency day</em>. These call names are
            deliberately different from CPCB pollution categories (CPCB "Severe" starts at 401) —
            a school action is not a pollution category.
          </li>
          <li className="flex gap-2.5">
            <span className="font-extrabold text-ink">3.</span>
            Scan upcoming hours inside the school's operating hours and days for low-AQI windows
            (AQI ≤ 100) long enough for a typical activity. If none fit, the app says so plainly
            instead of recommending a polluted period.
          </li>
          <li className="flex gap-2.5">
            <span className="font-extrabold text-ink">4.</span>
            Derive active alerts when current or forecast AQI crosses risk thresholds.
          </li>
        </ol>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-extrabold text-ink">Limitations</h2>
        <ul className="mt-3 list-disc space-y-2.5 pl-5 text-sm leading-relaxed text-slate-700">
          <li>
            <span className="font-semibold text-ink">Modelled, not measured.</span> Open-Meteo data comes from
            atmospheric models, not the CPCB monitoring station outside your school. Local sources (traffic jams,
            construction, stubble burning) may not be fully captured.
          </li>
          <li>
            <span className="font-semibold text-ink">Hourly, not 24-hour averaged.</span> See "indicative" above —
            spikes read higher than official daily AQI.
          </li>
          <li>
            <span className="font-semibold text-ink">Not medical advice, not a closure order.</span> The advisory is a
            planning aid. Children with asthma or other conditions should follow their doctor's action plan
            regardless of the call, and schools should follow their board and local authorities for closures.
          </li>
          <li>
            <span className="font-semibold text-ink">School store is persistent.</span> Registered schools, alert
            subscriptions, teacher action logs and bulletin state are stored in Amazon DynamoDB — they survive
            backend restarts.
          </li>
        </ul>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-extrabold text-ink">Built on AWS</h2>
        <div className="mt-3 space-y-3 text-sm leading-relaxed text-slate-700">
          <p>
            The <span className="font-semibold text-ink">Ask Saans</span> assistant is powered by the{' '}
            <span className="font-semibold text-ink">Strands Agents SDK</span> — AWS's open-source framework for
            building AI agents. The agent is given three tools (
            <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs">get_current_aqi</code>,{' '}
            <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs">get_forecast</code>,{' '}
            <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs">get_school_advisory</code>) and
            grounds every claim in tool output. If no model key is configured, the API transparently serves the
            rule-based fallback from the same advisory engine — and says so in the UI badge.
          </p>
          <p className="font-semibold text-ink">Live AWS deployment (SAM, ap-southeast-2):</p>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>
              <span className="font-semibold">AWS Lambda + API Gateway</span> serving the FastAPI app —
              search, AQI, forecast, advisory, alerts, schools, bulletins, activity planner, teacher
              action log, and the agent chat endpoint.
            </li>
            <li>
              <span className="font-semibold">Amazon DynamoDB</span> persists registered schools, alert
              subscriptions, teacher acknowledgements and bulletin state.
            </li>
            <li>
              <span className="font-semibold">Amazon EventBridge Scheduler</span> fires a daily 5:30 AM IST run
              generating bulletins for every registered school.
            </li>
            <li>
              <span className="font-semibold">Amazon SNS</span> delivers bulletins and material-change alerts to
              subscribed phones (SMS) and emails — with an opt-in confirmation step before delivery.
            </li>
          </ul>
        </div>
      </section>
    </div>
  );
}

# Saans — 3-Minute Demo Video Script

Record your screen at 1080p, mic on, steady pace. Times are guides — land the
bold lines. Total: ~3:00. The full loop: **school → recommendation → evidence →
activity plan → bulletin → teacher acknowledgement → action history.**

## 0:00–0:20 — The hook (problem)
> "Every October, North India's air turns hazardous — and 250 million students go
> to school with **zero protocol** for when it's unsafe to play outside. **Saans
> gives every school a morning breathing bulletin** — a clear call for the day,
> the evidence behind it, and a log of what the school actually did. Let me show
> you the whole loop."

## 0:20–0:50 — Dashboard: recommendation + evidence
- Open the app. Point at the gauge and the "Indicative · modelled" chip:
> "Live AQI for Patna — **[read the number and category]**. That chip matters:
> this is an indicative hourly model estimate, not an official CPCB 24-hour
> reading, and we label it everywhere."
- Open "Why this decision?":
> "And here's the part most apps skip — the evidence. The exact rule, the
> reference AQI, the dominant pollutant, the 6-hour peak, and the limitations.
> **Same decision object powers the dashboard, the bulletin, and the AI
> assistant — so they can never contradict each other.**"

## 0:50–1:30 — School → bulletin (English + Hindi)
- Schools tab → add a school, set hours 08:00–15:00 → open its bulletin:
> "A principal registers once, with the school's real hours. The bulletin gives
> today's call — **[read the call label]** — plus an activity plan: **[read the
> plan — e.g. 'Hold indoors' with the reason]**. Notice the windows are filtered
> to school hours — it will never recommend 5 PM for a school day, and it says
> plainly when no suitable window exists."
- Toggle हिंदी:
> "One tap, and the whole bulletin — call, checklist, disclaimer — is in Hindi,
> printable for the notice board. Copy or share sends the text to parent groups."

## 1:30–2:10 — Teacher acknowledgement → action history
- Type your name, click "PT moved indoors":
> "Here's the differentiator: guidance is useless if nobody acts on it. The
> teacher records what the school did — PT moved indoors, assembly rescheduled —
> stamped with today's advisory version. Duplicates are blocked, and the day's
> log builds up right here."
- Open the activity planner, try "Sports / 60 min / afternoon":
> "And the planner finds a real slot inside school hours — or tells you honestly
> to stay indoors, with the reason."

## 2:10–2:40 — Ask Saans + a demo scenario
- Ask Saans: *"Best time for morning PT?"*
> "The advisor is built on **Strands Agents SDK — AWS open source**. Watch: a
> morning question gets a morning answer, never an evening window — the fallback
> uses the same school-aware engine."
- (Optional) open `?demo=indoor_day`:
> "For judges: scripted demo scenarios — indoor day, worsening forecast, even a
> data outage — clearly badged, fully isolated from real records and alerts."

## 2:40–3:00 — AWS + honesty close
- Flash the Methodology page:
> "Deployed serverless on AWS: Lambda + API Gateway serve the API, DynamoDB
> persists schools and action logs, EventBridge fires the 5:30 AM bulletin run,
> SNS texts it to subscribed phones — with opt-in confirmation and
> material-change alerts that don't spam. **No child exercises on a bad-air day
> because nobody told the school.** Thank you."

---
**Checklist before you hit record:** backend running, frontend on `npm run dev`,
close extra tabs, 125% browser zoom. Demo URLs: append `?demo=normal_day`,
`?demo=indoor_day`, `?demo=worsening`, `?demo=outage` to the dashboard URL for
scripted scenarios (badged, isolated — safe to show).

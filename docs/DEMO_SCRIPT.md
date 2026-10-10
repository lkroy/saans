# Saans — 3-Minute Demo Video Script

Record your screen at 1080p, mic on, steady pace. Times are guides — land the
bold lines. Total: ~3:00.

## 0:00–0:20 — The hook (problem)
> "Every October, stubble-burning season pushes North India's air quality into
> the red. And 250 million students go to school with **zero protocol** for when
> it's unsafe to play outside. **Saans gives every school a morning breathing
> bulletin** — live air data, a clear call for the day, and an AI advisor for
> parents. Let me show you."

## 0:20–1:00 — Dashboard (live data)
- Open the app (Patna loads by default). Point at the gauge:
> "Live AQI for Patna right now — **[read the number and category off the
> gauge]**, driven by [dominant pollutant]. This is
> real data, pulled live from the Open-Meteo air quality API, scored on India's
> official CPCB scale."
- Scroll to the 48-hour forecast chart:
> "And here's the next 48 hours — you can see the peak hours tipping into
> **[read the worst category on the chart]**. The advisory banner turns that
> into a plain-language call, and these are the cleanest windows to schedule
> outdoor PT."

## 1:00–1:40 — Schools (the bulletin)
- Go to Schools, add "NIT Patna Model School", open its bulletin:
> "A principal registers once and gets this every morning: today's call, the
> peak to watch, and a checklist — move PT indoors, keep windows closed during
> peak hours. Hit print, and it's on the notice board in ten seconds."

## 1:40–2:20 — Ask Saans (the AI)
- Open Ask Saans, click the suggested question:
  *"My son has asthma — should he play football tomorrow?"*
> "The advisor is built on **Strands Agents SDK, AWS open source**. It pulls
> live AQI and the forecast through its tools and answers in plain language —
> with sources cited, not vibes. And if there's no model key configured, it
> says so and falls back to the same advisory engine — honestly."

## 2:20–2:50 — AWS + honesty (where AWS fits)
- Flash the Methodology page, then the repo's `infra/` folder:
> "For deployment it's serverless on AWS: Lambda and API Gateway serve the API,
> EventBridge fires the 5:30 AM bulletin run, DynamoDB stores schools, SNS sends
> alerts — all free-tier friendly via this SAM template. And we're honest about
> data: modelled versus measured is labeled everywhere, because a school acting
> on this deserves to know what it's looking at."

## 2:50–3:00 — Close
> "Saans — Air track. One small problem, solved end to end: **no child exercises
> on a Severe day because nobody told the school.** Thank you."

---
**Checklist before you hit record:** backend running (`uvicorn app.main:app --port 8000`),
frontend on `npm run dev`, Gemini key in `backend/.env` (optional but better for the
Ask Saans segment), close extra tabs, 125% browser zoom for readability.

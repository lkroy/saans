import type { Category, PollutantMap } from './api';

/** CPCB color system (from API contract). */
export const CATEGORY_COLORS: Record<Category, string> = {
  Good: '#2ca02c',
  Satisfactory: '#7ac143',
  Moderate: '#ffbf00',
  Poor: '#ff7f0e',
  'Very Poor': '#d62728',
  Severe: '#8b0000',
};

/** CPCB AQI bands for the gauge. */
export const AQI_BANDS: { from: number; to: number; category: Category }[] = [
  { from: 0, to: 50, category: 'Good' },
  { from: 51, to: 100, category: 'Satisfactory' },
  { from: 101, to: 200, category: 'Moderate' },
  { from: 201, to: 300, category: 'Poor' },
  { from: 301, to: 400, category: 'Very Poor' },
  { from: 401, to: 500, category: 'Severe' },
];

export const POLLUTANT_META: Record<keyof PollutantMap, { label: string; unit: string; blurb: string }> = {
  pm2_5: { label: 'PM2.5', unit: 'µg/m³', blurb: 'Fine particles — the main driver of health risk.' },
  pm10: { label: 'PM10', unit: 'µg/m³', blurb: 'Coarse dust and smoke particles.' },
  o3: { label: 'O₃', unit: 'µg/m³', blurb: 'Ground-level ozone, peaks in afternoon sun.' },
  no2: { label: 'NO₂', unit: 'µg/m³', blurb: 'Traffic and combustion exhaust.' },
  so2: { label: 'SO₂', unit: 'µg/m³', blurb: 'Industrial and coal-burning emissions.' },
  co: { label: 'CO', unit: 'µg/m³', blurb: 'Carbon monoxide from incomplete combustion.' },
};

const hourFmt = new Intl.DateTimeFormat('en-IN', { hour: 'numeric', hour12: true, timeZone: 'Asia/Kolkata' });
const dayHourFmt = new Intl.DateTimeFormat('en-IN', {
  weekday: 'short',
  hour: 'numeric',
  hour12: true,
  timeZone: 'Asia/Kolkata',
});
const dayFmt = new Intl.DateTimeFormat('en-IN', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Kolkata',
});
const fullFmt = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  hour: 'numeric',
  minute: '2-digit',
  hour12: true,
  timeZone: 'Asia/Kolkata',
});

/** "10 AM" for a chart axis tick. */
export function fmtHour(iso: string): string {
  return hourFmt.format(new Date(iso));
}

/** "Fri, 10 AM". */
export function fmtDayHour(iso: string): string {
  return dayHourFmt.format(new Date(iso));
}

/** "Friday, 10 October". */
export function fmtDateLong(iso: string): string {
  return dayFmt.format(new Date(iso));
}

/** "10 Oct, 08:00 AM". */
export function fmtDateTime(iso: string): string {
  return fullFmt.format(new Date(iso));
}

/** "10 AM – 1 PM" window label from two ISO datetimes. */
export function fmtWindow(start: string, end: string): string {
  return `${fmtHour(start)} – ${fmtHour(end)}`;
}

export function categoryColor(category: Category): string {
  return CATEGORY_COLORS[category] ?? '#64748b';
}

/** Pick a readable text color (white/black) for a given background hex. */
export function textOn(hex: string): string {
  const c = hex.replace('#', '');
  const r = parseInt(c.slice(0, 2), 16);
  const g = parseInt(c.slice(2, 4), 16);
  const b = parseInt(c.slice(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.62 ? '#1a2b3c' : '#ffffff';
}

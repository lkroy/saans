import { AQI_BANDS, categoryColor, textOn } from '../lib/utils';
import type { Category } from '../lib/api';

const MAX_AQI = 500;
const SIZE = 320;
const CX = SIZE / 2;
const CY = SIZE / 2 + 40;
const R = 120;
const STROKE = 26;

function polar(aqi: number, radius: number): { x: number; y: number } {
  // 0 AQI → 180°, 500 AQI → 0° (semicircle, left to right)
  const angle = Math.PI - (Math.min(Math.max(aqi, 0), MAX_AQI) / MAX_AQI) * Math.PI;
  return { x: CX + radius * Math.cos(angle), y: CY - radius * Math.sin(angle) };
}

function arcPath(from: number, to: number, radius: number): string {
  const a = polar(from, radius);
  const b = polar(to, radius);
  return `M ${a.x.toFixed(2)} ${a.y.toFixed(2)} A ${radius} ${radius} 0 0 1 ${b.x.toFixed(2)} ${b.y.toFixed(2)}`;
}

export default function AQIGauge({ aqi, category }: { aqi: number; category: Category }) {
  const color = categoryColor(category);
  const needle = polar(aqi, R);
  const clamped = Math.min(Math.max(aqi, 0), MAX_AQI);

  return (
    <div className="flex flex-col items-center">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="w-full max-w-[340px]" role="img" aria-label={`AQI ${aqi}, ${category}`}>
        {/* Track: muted category bands */}
        {AQI_BANDS.map((b) => (
          <path
            key={b.category}
            d={arcPath(b.from, b.to, R)}
            fill="none"
            stroke={categoryColor(b.category)}
            strokeWidth={STROKE}
            strokeLinecap="butt"
            opacity={0.28}
          />
        ))}
        {/* Filled value arc up to the current AQI */}
        <path
          d={arcPath(0, clamped, R)}
          fill="none"
          stroke={color}
          strokeWidth={STROKE}
          strokeLinecap="round"
          opacity={0.95}
        />
        {/* Needle */}
        <line x1={CX} y1={CY} x2={needle.x} y2={needle.y} stroke="#1a2b3c" strokeWidth={3} strokeLinecap="round" />
        <circle cx={CX} cy={CY} r={9} fill="#1a2b3c" />
        <circle cx={CX} cy={CY} r={3.5} fill="#fff" />
      </svg>
      <div className="-mt-16 flex flex-col items-center pb-2">
        <span className="text-5xl font-extrabold tracking-tight text-ink">{aqi}</span>
        <span
          className="mt-2 rounded-full px-4 py-1 text-sm font-bold"
          style={{ backgroundColor: color, color: textOn(color) }}
        >
          {category}
        </span>
      </div>
    </div>
  );
}

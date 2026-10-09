import { Link, NavLink, useLocation as useRoute } from 'react-router-dom';
import { useLocation } from '../lib/location';

const NAV = [
  { to: '/', label: 'Dashboard' },
  { to: '/schools', label: 'Schools' },
  { to: '/ask', label: 'Ask Saans' },
  { to: '/methodology', label: 'Methodology' },
];

export default function Header() {
  const { location } = useLocation();
  const route = useRoute();
  const isBulletinPrint = route.pathname.startsWith('/schools') && new URLSearchParams(route.search).get('print') === '1';

  return (
    <header className={`no-print sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur ${isBulletinPrint ? 'hidden' : ''}`}>
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
        <Link to="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-aqi-good text-lg font-bold text-white" aria-hidden>
            स
          </span>
          <span className="leading-tight">
            <span className="block text-base font-extrabold tracking-tight text-ink">Saans</span>
            <span className="block text-[11px] font-medium uppercase tracking-widest text-slate-500">School Air Safety</span>
          </span>
        </Link>
        <nav className="flex flex-wrap items-center gap-1 text-sm font-medium" aria-label="Primary">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `rounded-full px-3 py-1.5 transition-colors ${
                  isActive ? 'bg-ink text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-ink'
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto hidden items-center gap-1.5 text-xs text-slate-500 md:flex" title={`${location.lat.toFixed(2)}, ${location.lon.toFixed(2)}`}>
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5Z" />
          </svg>
          <span className="max-w-48 truncate font-medium">{location.label}</span>
        </div>
      </div>
    </header>
  );
}

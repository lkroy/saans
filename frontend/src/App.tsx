import { Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import Schools from './pages/Schools';
import Ask from './pages/Ask';
import Methodology from './pages/Methodology';

export default function App() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto w-full max-w-6xl px-4 pb-16 pt-6 sm:px-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/schools" element={<Schools />} />
          <Route path="/ask" element={<Ask />} />
          <Route path="/methodology" element={<Methodology />} />
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </main>
      <footer className="no-print border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>
            <span className="font-semibold text-slate-700">Saans</span> · School Air Safety — a WeMakeDevs
            Environmental Hacks (Air track) entry.
          </p>
          <p>Indicative hourly AQI · modelled data (Open-Meteo). Not a medical device.</p>
        </div>
      </footer>
    </div>
  );
}

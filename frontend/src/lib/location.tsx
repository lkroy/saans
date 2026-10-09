import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { SearchResult } from './api';

export interface Location {
  label: string;
  lat: number;
  lon: number;
}

const DEFAULT_LOCATION: Location = { label: 'Patna, Bihar, India', lat: 25.5941, lon: 85.1376 };
const STORAGE_KEY = 'saans-location';

interface LocationContextValue {
  location: Location;
  setLocation: (loc: Location) => void;
  setFromSearch: (r: SearchResult) => void;
}

const LocationContext = createContext<LocationContextValue | null>(null);

function loadStored(): Location {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Location;
      if (typeof parsed.lat === 'number' && typeof parsed.lon === 'number' && parsed.label) {
        return parsed;
      }
    }
  } catch {
    /* ignore */
  }
  return DEFAULT_LOCATION;
}

export function LocationProvider({ children }: { children: ReactNode }) {
  const [location, setLocationState] = useState<Location>(loadStored);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(location));
    } catch {
      /* ignore */
    }
  }, [location]);

  const setLocation = (loc: Location) => setLocationState(loc);
  const setFromSearch = (r: SearchResult) =>
    setLocationState({
      label: `${r.name}${r.admin1 ? `, ${r.admin1}` : ''}${r.country ? `, ${r.country}` : ''}`,
      lat: r.lat,
      lon: r.lon,
    });

  return (
    <LocationContext.Provider value={{ location, setLocation, setFromSearch }}>
      {children}
    </LocationContext.Provider>
  );
}

export function useLocation(): LocationContextValue {
  const ctx = useContext(LocationContext);
  if (!ctx) throw new Error('useLocation must be used inside LocationProvider');
  return ctx;
}

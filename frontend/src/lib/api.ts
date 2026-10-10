/**
 * Typed API client for the Saans backend (see ~/workspace/saans/API_CONTRACT.md).
 * Base URL defaults to http://localhost:8000 and can be overridden with VITE_API_URL.
 */

const API_BASE =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/+$/, '') ?? 'http://localhost:8000';

export type Category = 'Good' | 'Satisfactory' | 'Moderate' | 'Poor' | 'Very Poor' | 'Severe';
export type CallLevel = 'clear' | 'caution' | 'indoor' | 'severe';

export interface SearchResult {
  name: string;
  admin1: string;
  country: string;
  lat: number;
  lon: number;
}

export interface PollutantMap {
  pm2_5: number;
  pm10: number;
  o3: number;
  no2: number;
  so2: number;
  co: number;
}

export interface CurrentAqi {
  aqi: number;
  category: Category;
  color: string;
  dominant: keyof PollutantMap;
  pollutants: PollutantMap;
  updated_at: string;
  source: string;
  data_status: string;
}

export interface ForecastHour {
  time: string;
  aqi: number;
  category: Category;
  pm2_5: number;
  pm10: number;
}

export interface ForecastResponse {
  hours: ForecastHour[];
  source: string;
  data_status: string;
}

export interface AdvisoryCall {
  level: CallLevel;
  headline: string;
  detail: string;
}

export interface BestWindow {
  start: string;
  end: string;
  label: string;
  aqi: number;
}

export interface AdvisoryResponse {
  call: AdvisoryCall;
  aqi_now: number;
  peak_6h: { aqi: number; at: string };
  best_windows: BestWindow[];
  wind: WindStory | null;
  generated_at: string;
}

export interface WindStory {
  direction: string;
  direction_label: string;
  degrees: number;
  speed_kmh: number;
  headline: string;
  detail: string;
}

export interface Subscription {
  channel: 'sms' | 'email';
  target: string;
  arn: string;
  status: string;
}

export interface AlertItem {
  severity: 'warn' | 'critical';
  title: string;
  detail: string;
  at: string;
}

export interface School {
  id: string;
  name: string;
  city: string;
  lat: number;
  lon: number;
  contact?: string;
  created_at: string;
  subscriptions?: Subscription[];
}

export interface Bulletin {
  school: { id: string; name: string; city: string };
  date: string;
  call: AdvisoryCall;
  aqi_now: number;
  category: Category;
  peak_today: { aqi: number; at: string };
  best_windows: BestWindow[];
  checklist: string[];
  generated_at: string;
}

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatResponse {
  reply: string;
  agent: 'strands' | 'fallback';
  sources: string[];
}

export interface HealthResponse {
  status: string;
  agent: 'strands' | 'fallback';
  version: string;
}

export class ApiError extends Error {
  readonly kind: 'backend-unreachable' | 'not-found' | 'validation' | 'server' | 'unknown';

  constructor(kind: ApiError['kind'], message: string) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(
      'backend-unreachable',
      'Could not reach the Saans backend. Start it with: uvicorn app.main:app --port 8000',
    );
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* keep default */
    }
    const kind =
      res.status === 404 ? 'not-found' : res.status === 422 ? 'validation' : res.status >= 500 ? 'server' : 'unknown';
    throw new ApiError(kind, detail);
  }

  return (await res.json()) as T;
}

export const api = {
  health(): Promise<HealthResponse> {
    return request<HealthResponse>('/api/health');
  },
  search(q: string, limit = 8): Promise<{ results: SearchResult[] }> {
    return request<{ results: SearchResult[] }>(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`);
  },
  currentAqi(lat: number, lon: number): Promise<CurrentAqi> {
    return request<CurrentAqi>(`/api/aqi/current?lat=${lat}&lon=${lon}`);
  },
  forecast(lat: number, lon: number, hours = 48): Promise<ForecastResponse> {
    return request<ForecastResponse>(`/api/aqi/forecast?lat=${lat}&lon=${lon}&hours=${hours}`);
  },
  advisory(lat: number, lon: number): Promise<AdvisoryResponse> {
    return request<AdvisoryResponse>(`/api/advisory?lat=${lat}&lon=${lon}`);
  },
  alerts(lat: number, lon: number): Promise<{ alerts: AlertItem[] }> {
    return request<{ alerts: AlertItem[] }>(`/api/alerts?lat=${lat}&lon=${lon}`);
  },
  listSchools(): Promise<{ schools: School[] }> {
    return request<{ schools: School[] }>('/api/schools');
  },
  addSchool(body: { name: string; city: string; lat: number; lon: number; contact?: string }): Promise<School> {
    return request<School>('/api/schools', { method: 'POST', body: JSON.stringify(body) });
  },
  deleteSchool(id: string): Promise<{ deleted: boolean }> {
    return request<{ deleted: boolean }>(`/api/schools/${id}`, { method: 'DELETE' });
  },
  bulletin(id: string): Promise<Bulletin> {
    return request<Bulletin>(`/api/schools/${id}/bulletin`);
  },
  getSchool(id: string): Promise<School> {
    return request<School>(`/api/schools/${id}`);
  },
  subscribe(id: string, channel: 'sms' | 'email', target: string): Promise<{ subscription: Subscription; note: string }> {
    return request<{ subscription: Subscription; note: string }>(`/api/schools/${id}/subscriptions`, {
      method: 'POST',
      body: JSON.stringify({ channel, target }),
    });
  },
  chat(message: string, lat: number, lon: number, history: ChatMessage[]): Promise<ChatResponse> {
    return request<ChatResponse>('/api/agent/chat', {
      method: 'POST',
      body: JSON.stringify({ message, lat, lon, history }),
    });
  },
};

import { useEffect, useRef, useState } from 'react';
import { api, ApiError, type ChatMessage } from '../lib/api';
import { useLocation } from '../lib/location';

const SUGGESTIONS = [
  'Should kids play outside today?',
  'Best time for morning PT?',
  'My child has asthma — any precautions?',
];

interface ChatBubble extends ChatMessage {
  agent?: 'strands' | 'fallback';
  sources?: string[];
  error?: boolean;
}

function AgentBadge({ agent }: { agent: 'strands' | 'fallback' }) {
  const isStrands = agent === 'strands';
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest ${
        isStrands ? 'bg-violet-100 text-violet-800' : 'bg-slate-200 text-slate-600'
      }`}
      title={
        isStrands
          ? 'Answered by the Strands agent with live AQI tools'
          : 'Rule-based guidance from the Saans advisory engine'
      }
    >
      <span className={`inline-block h-1.5 w-1.5 rounded-full ${isStrands ? 'bg-violet-600' : 'bg-slate-500'}`} />
      AI: {isStrands ? 'Strands agent' : 'Rule-based guidance'}
    </span>
  );
}

export default function Ask() {
  const { location } = useLocation();
  const [messages, setMessages] = useState<ChatBubble[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [backendDown, setBackendDown] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setSending(true);
    setBackendDown(false);
    const history: ChatMessage[] = [...messages, { role: 'user' as const, content: trimmed }].map((m) => ({
      role: m.role,
      content: m.content,
    }));
    setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
    setInput('');
    try {
      const res = await api.chat(trimmed, location.lat, location.lon, history.slice(0, -1));
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.reply, agent: res.agent, sources: res.sources },
      ]);
    } catch (e) {
      const unreachable = e instanceof ApiError && e.kind === 'backend-unreachable';
      setBackendDown(unreachable);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: unreachable
            ? 'I can’t reach the Saans backend, so I can’t check live air quality. Start it with: uvicorn app.main:app --port 8000, then ask again.'
            : e instanceof Error
              ? `Something went wrong: ${e.message}`
              : 'Something went wrong. Please try again.',
          error: true,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col" style={{ minHeight: '70vh' }}>
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">Ask Saans</h1>
        <p className="mt-1 text-sm text-slate-500">
          Questions about air quality for <span className="font-semibold text-ink">{location.label}</span> — the
          assistant checks live AQI before answering.
        </p>
      </div>

      <div className="mt-6 flex-1 space-y-4 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        {messages.length === 0 && !sending && (
          <div className="flex h-full flex-col items-center justify-center py-10 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-aqi-good text-2xl font-bold text-white" aria-hidden>
              स
            </span>
            <p className="mt-4 max-w-sm text-sm text-slate-600">
              Ask about outdoor play, PT timings, asthma precautions, masks, or school-day calls — answers are
              grounded in live AQI data for {location.label.split(',')[0]}.
            </p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-slate-300 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-ink hover:bg-white"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'rounded-br-md bg-ink text-white'
                  : m.error
                    ? 'rounded-bl-md border border-red-200 bg-red-50 text-slate-800'
                    : 'rounded-bl-md bg-slate-100 text-slate-800'
              }`}
            >
              {m.role === 'assistant' && !m.error && m.agent && (
                <div className="mb-2">
                  <AgentBadge agent={m.agent} />
                </div>
              )}
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.role === 'assistant' && !m.error && m.sources && m.sources.length > 0 && (
                <p className="mt-2.5 border-t border-slate-200/70 pt-2 text-[11px] leading-relaxed text-slate-500">
                  Sources: {m.sources.join(' · ')}
                </p>
              )}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-md bg-slate-100 px-4 py-3">
              <div className="flex gap-1.5" aria-label="Thinking">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-2 w-2 animate-bounce rounded-full bg-slate-400"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {backendDown && (
        <p className="mt-3 rounded-xl bg-red-50 px-4 py-2.5 text-xs text-red-700">
          Backend unreachable — start it with{' '}
          <code className="font-mono">uvicorn app.main:app --port 8000</code>
        </p>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="no-print mt-4 flex gap-2"
      >
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about air quality and school activities…"
          className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm shadow-sm outline-none focus:border-ink focus:ring-2 focus:ring-ink/10"
          aria-label="Ask Saans a question"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="rounded-xl bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
        >
          Send
        </button>
      </form>
      <p className="mt-2 text-center text-[11px] text-slate-400">
        General information only — for medical concerns, consult a doctor.
      </p>
    </div>
  );
}

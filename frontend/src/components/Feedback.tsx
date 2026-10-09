import { ApiError } from '../lib/api';

export function SkeletonCard({ className = '' }: { className?: string }) {
  return <div className={`skeleton rounded-2xl ${className}`} aria-hidden />;
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6" aria-label="Loading">
      <SkeletonCard className="h-16" />
      <div className="grid gap-6 lg:grid-cols-3">
        <SkeletonCard className="h-80" />
        <div className="space-y-6 lg:col-span-2">
          <SkeletonCard className="h-32" />
          <SkeletonCard className="h-48" />
        </div>
      </div>
      <SkeletonCard className="h-64" />
    </div>
  );
}

/** Friendly error panel with a clear backend-unreachable message. */
export function ErrorState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  const isApi = error instanceof ApiError;
  const unreachable = isApi && error.kind === 'backend-unreachable';
  const title = unreachable ? "Can't reach the Saans backend" : 'Something went wrong';
  const message = isApi
    ? error.message
    : error instanceof Error
      ? error.message
      : 'An unexpected error occurred.';

  return (
    <div className="flex flex-col items-center rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center shadow-sm">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-xl" aria-hidden>
        ⚠
      </span>
      <h2 className="mt-4 text-lg font-bold text-ink">{title}</h2>
      <p className="mt-2 max-w-md text-sm text-slate-600">{message}</p>
      {unreachable && (
        <code className="mt-4 rounded-lg bg-slate-900 px-4 py-2.5 font-mono text-xs text-green-300">
          uvicorn app.main:app --port 8000
        </code>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-6 rounded-xl bg-ink px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90"
        >
          Try again
        </button>
      )}
    </div>
  );
}

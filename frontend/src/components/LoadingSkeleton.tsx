/**
 * LoadingSkeleton — reusable shimmer/pulse skeletons for async views.
 *
 * Phase 8 — Polish, Integration Testing, and Deployment
 */

interface SkeletonProps {
  /** Number of skeleton rows to show */
  rows?: number;
  /** Optional label shown above the skeleton */
  label?: string;
  /** Variant: 'table' | 'chart' | 'card' | 'text' */
  variant?: 'table' | 'chart' | 'card' | 'text';
}

function SkeletonPulse({ className = '' }: { className?: string }) {
  return (
    <div
      className={`skeleton-shimmer rounded-lg ${className}`}
      aria-hidden="true"
    />
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div data-testid="skeleton-table" role="status" aria-label="Loading table data">
      <div className="space-y-3">
        {/* Header row */}
        <div className="flex gap-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <SkeletonPulse key={i} className="h-4 flex-1" />
          ))}
        </div>
        {/* Data rows */}
        {Array.from({ length: rows }, (_, idx) => (
          <div key={idx} className="flex gap-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <SkeletonPulse key={i} className="h-3 flex-1" />
            ))}
          </div>
        ))}
      </div>
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export function ChartSkeleton() {
  const heights = [60, 80, 45, 90, 70, 55, 85, 40];
  return (
    <div
      data-testid="skeleton-chart"
      role="status"
      aria-label="Loading chart"
      className="glass-card p-6"
    >
      <div className="flex items-end gap-3 h-48">
        {heights.map((h, idx) => (
          <div
            key={idx}
            className="flex-1 skeleton-shimmer rounded-lg"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
      <SkeletonPulse className="h-3 w-full mt-4" />
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div
      data-testid="skeleton-card"
      role="status"
      aria-label="Loading content"
      className="glass-card p-5 space-y-3"
    >
      <SkeletonPulse className="h-5 w-1/3" />
      {Array.from({ length: rows }, (_, idx) => (
        <SkeletonPulse key={idx} className="h-3 w-full" />
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export function SummarySkeleton() {
  return (
    <div
      data-testid="skeleton-summary"
      role="status"
      aria-label="Loading summary"
      className="flex flex-wrap gap-4"
    >
      {[1, 2, 3].map((i) => (
        <SkeletonPulse key={i} className="h-4 w-32" />
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export default function LoadingSkeleton({ rows = 5, label, variant = 'table' }: SkeletonProps) {
  return (
    <div className="space-y-4" data-testid="loading-skeleton">
      {label && (
        <p className="text-sm text-gray-400">{label}</p>
      )}
      {variant === 'table' && <TableSkeleton rows={rows} />}
      {variant === 'chart' && <ChartSkeleton />}
      {variant === 'card' && <CardSkeleton rows={rows} />}
      {variant === 'text' && (
        <div role="status" aria-label="Loading text" className="space-y-2">
          {Array.from({ length: rows }, (_, idx) => (
            <SkeletonPulse key={idx} className={`h-3 ${idx === rows - 1 ? 'w-2/3' : 'w-full'}`} />
          ))}
          <span className="sr-only">Loading…</span>
        </div>
      )}
    </div>
  );
}

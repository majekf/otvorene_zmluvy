/**
 * SeverityIndicator Component (Phase 4)
 *
 * Visual severity score indicator (color-coded dot or bar).
 * Severity is a value from 0.0 to 1.0.
 */

interface SeverityIndicatorProps {
  severity: number;
  size?: 'sm' | 'md';
}

function severityColor(severity: number): string {
  if (severity >= 0.7) return 'bg-red-500';
  if (severity >= 0.4) return 'bg-yellow-500';
  return 'bg-green-500';
}

function severityLabel(severity: number): string {
  if (severity >= 0.7) return 'High';
  if (severity >= 0.4) return 'Medium';
  return 'Low';
}

export default function SeverityIndicator({ severity, size = 'sm' }: SeverityIndicatorProps) {
  const dotSize = size === 'sm' ? 'w-2.5 h-2.5' : 'w-3.5 h-3.5';
  const color = severityColor(severity);
  const label = severityLabel(severity);

  return (
    <span
      data-testid="severity-indicator"
      data-severity={severity}
      className="inline-flex items-center gap-1"
      title={`Severity: ${(severity * 100).toFixed(0)}% (${label})`}
    >
      <span className={`${dotSize} rounded-full ${color} inline-block`} />
      {size === 'md' && (
        <span className="text-xs text-slate-600">{label}</span>
      )}
    </span>
  );
}

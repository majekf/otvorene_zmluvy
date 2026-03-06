/**
 * Utility functions for formatting values in the UI.
 */

/** Format a number as EUR currency. */
export function formatEur(value: number | null | undefined): string {
  if (value == null) return '—';
  return value.toLocaleString('sk-SK', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  });
}

/** Format a large number with k/M suffix. */
export function formatCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M €`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(0)}k €`;
  return `${value.toFixed(0)} €`;
}

/** Format a date string for display. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  return iso;
}

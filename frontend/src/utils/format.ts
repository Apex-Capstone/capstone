export function formatPercent(value?: number | null): string {
  if (value === undefined || value === null) return '—'
  return `${value.toFixed(1)}%`
}

/** Whole-number percent (e.g. analytics tables). */
export function formatPercentWhole(value?: number | null): string {
  if (value === undefined || value === null) return '—'
  return `${Math.round(value)}%`
}


export function formatPercent(value?: number | null): string {
  if (value === undefined || value === null) return '—'
  return `${value.toFixed(1)}%`
}


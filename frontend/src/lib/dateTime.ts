const UTC_TIME_SUFFIX_RE = /(?:[zZ]|[+-]\d{2}:\d{2})$/
const DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}$/

function normalizeUtcTimestamp(value: string): string {
  const trimmed = value.trim()
  if (!trimmed || DATE_ONLY_RE.test(trimmed) || UTC_TIME_SUFFIX_RE.test(trimmed)) {
    return trimmed
  }

  return trimmed.includes('T') ? `${trimmed}Z` : trimmed
}

export function parseUtcDateTime(value: string | null | undefined): Date | null {
  if (!value) return null

  const parsed = new Date(normalizeUtcTimestamp(value))
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function utcTimestampMs(value: string | null | undefined): number {
  return parseUtcDateTime(value)?.getTime() ?? Number.NaN
}

export function formatDateTimeInUserTimeZone(
  value: string | null | undefined,
  options?: Intl.DateTimeFormatOptions,
  fallback = '—'
): string {
  const parsed = parseUtcDateTime(value)
  return parsed ? parsed.toLocaleString(undefined, options) : fallback
}

export function formatDateInUserTimeZone(
  value: string | null | undefined,
  options?: Intl.DateTimeFormatOptions,
  fallback = '—'
): string {
  const parsed = parseUtcDateTime(value)
  return parsed ? parsed.toLocaleDateString(undefined, options) : fallback
}

export function formatTimeInUserTimeZone(
  value: string | null | undefined,
  options?: Intl.DateTimeFormatOptions,
  fallback = '—'
): string {
  const parsed = parseUtcDateTime(value)
  return parsed ? parsed.toLocaleTimeString(undefined, options) : fallback
}

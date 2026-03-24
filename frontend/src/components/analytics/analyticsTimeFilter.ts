import type { TraineeSessionAnalytics } from '@/types/analytics'

export type AnalyticsTimeRange = 'last7_sessions' | 'last30_days' | 'all_time'

export const ANALYTICS_TIME_RANGE_OPTIONS: ReadonlyArray<{
  value: AnalyticsTimeRange
  label: string
}> = [
  { value: 'last7_sessions', label: 'Last 7 sessions' },
  { value: 'last30_days', label: 'Last 30 days' },
  { value: 'all_time', label: 'All time' },
]

/** Default: full history so first-time visitors always see their data. */
export const DEFAULT_ANALYTICS_TIME_RANGE: AnalyticsTimeRange = 'all_time'

/**
 * Parses session completion time from `createdAt`.
 * Returns `null` if the value is missing or not a valid date.
 */
export function sessionCompletionTimeMs(createdAt: string | undefined | null): number | null {
  if (createdAt == null || createdAt === '') return null
  const ms = Date.parse(createdAt)
  return Number.isFinite(ms) ? ms : null
}

function compareByCompletionAsc(a: TraineeSessionAnalytics, b: TraineeSessionAnalytics): number {
  const ta = sessionCompletionTimeMs(a.createdAt)
  const tb = sessionCompletionTimeMs(b.createdAt)
  if (ta == null && tb == null) return a.sessionId - b.sessionId
  if (ta == null) return 1
  if (tb == null) return -1
  if (ta !== tb) return ta - tb
  return a.sessionId - b.sessionId
}

function compareByCompletionDesc(a: TraineeSessionAnalytics, b: TraineeSessionAnalytics): number {
  const ta = sessionCompletionTimeMs(a.createdAt)
  const tb = sessionCompletionTimeMs(b.createdAt)
  if (ta == null && tb == null) return b.sessionId - a.sessionId
  if (ta == null) return 1
  if (tb == null) return -1
  if (ta !== tb) return tb - ta
  return b.sessionId - a.sessionId
}

/** Start of local calendar day, `daysAgo` days before today. */
function getLocalStartOfDayDaysAgo(daysAgo: number): number {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  d.setHours(0, 0, 0, 0)
  return d.getTime()
}

/**
 * Returns sessions for the selected range, sorted oldest → newest (chart order).
 * Uses `createdAt` as the session completion timestamp (API field).
 */
export function filterAnalyticsSessionsByTimeRange(
  sessions: TraineeSessionAnalytics[],
  range: AnalyticsTimeRange
): TraineeSessionAnalytics[] {
  if (sessions.length === 0) return []

  if (range === 'all_time') {
    return [...sessions].sort(compareByCompletionAsc)
  }

  if (range === 'last7_sessions') {
    const newestFirst = [...sessions].sort(compareByCompletionDesc)
    const slice = newestFirst.slice(0, 7)
    return slice.sort(compareByCompletionAsc)
  }

  // last30_days — rolling window from start of today − 30 (local)
  const cutoffMs = getLocalStartOfDayDaysAgo(30)
  return sessions
    .filter((s) => {
      const t = sessionCompletionTimeMs(s.createdAt)
      if (t == null) return false
      return t >= cutoffMs
    })
    .sort(compareByCompletionAsc)
}

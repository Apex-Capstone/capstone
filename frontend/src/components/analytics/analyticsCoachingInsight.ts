import type { TraineeSessionAnalytics } from '@/types/analytics'

type SummaryNonEmpty = {
  empty: false
  empathy: number
  communication: number
  spikes: number
  overall: number
  total: number
}

function isCommunicationTrendImproving(sessions: TraineeSessionAnalytics[]): boolean {
  if (sessions.length < 2) return false
  const mid = Math.floor(sessions.length / 2)
  if (mid < 1 || mid >= sessions.length) return false
  const early = sessions.slice(0, mid)
  const late = sessions.slice(mid)
  const avg = (items: TraineeSessionAnalytics[]) =>
    items.reduce((sum, s) => sum + s.communicationScore, 0) / items.length
  return avg(late) > avg(early)
}

/**
 * Coaching-style copy for the analytics Insight card (filtered sessions + aggregates).
 */
export function getAnalyticsCoachingInsight(
  filteredSessions: TraineeSessionAnalytics[],
  summary: { empty: true } | SummaryNonEmpty
): string {
  if (filteredSessions.length === 0) {
    return 'No sessions in this time range. Try a different time filter or complete more sessions.'
  }

  if (summary.empty) {
    return 'No sessions in this time range to analyze yet.'
  }

  if (summary.empathy < 20) {
    return 'Your empathy responses are currently low. Try acknowledging patient emotions before providing medical information.'
  }

  if (summary.spikes > summary.empathy) {
    return 'You cover SPIKES stages but empathy responses could improve.'
  }

  if (isCommunicationTrendImproving(filteredSessions)) {
    return 'Your communication scores improved in recent sessions. Keep practicing structured responses.'
  }

  return 'Complete more sessions to unlock deeper insights into your communication development.'
}

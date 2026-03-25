import { Info } from 'lucide-react'

/** Show a gentle “early progress” note when total completed sessions are below this count. */
export const ANALYTICS_LOW_DATA_SESSION_THRESHOLD = 3

type AnalyticsLowDataHintProps = {
  /** Total completed sessions (all-time from the loaded dataset). */
  sessionCount: number
}

/**
 * Subtle banner when a trainee has only a few sessions — trends are still shown; this sets expectations.
 */
export function AnalyticsLowDataHint({ sessionCount }: AnalyticsLowDataHintProps) {
  if (sessionCount < 1 || sessionCount >= ANALYTICS_LOW_DATA_SESSION_THRESHOLD) {
    return null
  }

  return (
    <div
      className="flex gap-3 rounded-lg border border-gray-200 bg-slate-50/90 px-4 py-3 text-left shadow-sm"
      role="status"
    >
      <span className="mt-0.5 shrink-0 text-gray-400" aria-hidden>
        <Info className="h-4 w-4" strokeWidth={2} />
      </span>
      <p className="text-sm leading-relaxed text-gray-700">
        <span className="font-medium text-gray-900">You&apos;re building your baseline.</span>{' '}
        Averages and trend lines become more useful as you complete more sessions—keep practicing,
        and check back here to see your progress take shape.
      </p>
    </div>
  )
}

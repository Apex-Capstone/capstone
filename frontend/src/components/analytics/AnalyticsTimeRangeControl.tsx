import { cn } from '@/lib/utils'
import {
  ANALYTICS_TIME_RANGE_OPTIONS,
  type AnalyticsTimeRange,
} from '@/components/analytics/analyticsTimeFilter'

type AnalyticsTimeRangeControlProps = {
  value: AnalyticsTimeRange
  onChange: (value: AnalyticsTimeRange) => void
  className?: string
  disabled?: boolean
}

/**
 * Compact segmented control for analytics time range (trainee dashboard).
 */
export function AnalyticsTimeRangeControl({
  value,
  onChange,
  className,
  disabled,
}: AnalyticsTimeRangeControlProps) {
  return (
    <div
      className={cn(
        'inline-flex flex-wrap justify-end rounded-lg border border-gray-200 bg-white p-0.5 shadow-sm',
        className
      )}
      role="group"
      aria-label="Time range"
    >
      {ANALYTICS_TIME_RANGE_OPTIONS.map((opt) => {
        const active = value === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            disabled={disabled}
            onClick={() => onChange(opt.value)}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-1',
              disabled && 'cursor-not-allowed opacity-50',
              active
                ? 'bg-gray-900 text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            )}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

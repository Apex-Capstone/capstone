import { Info } from 'lucide-react'
import { cn } from '@/lib/utils'

type MetricInfoTooltipProps = {
  description: string
  className?: string
  /** Visually hidden label for assistive tech (defaults to description) */
  ariaLabel?: string
}

/**
 * Subtle info trigger with a concise floating hint on hover/focus.
 */
export function MetricInfoTooltip({ description, className, ariaLabel }: MetricInfoTooltipProps) {
  return (
    <span className={cn('group relative inline-flex align-middle', className)}>
      <button
        type="button"
        className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-gray-400 transition-colors hover:text-gray-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/35 focus-visible:ring-offset-1"
        aria-label={ariaLabel ?? description}
      >
        <Info className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-[min(260px,calc(100vw-2rem))] -translate-x-1/2 rounded-md border border-gray-200 bg-white px-3 py-2 text-left text-xs leading-snug text-gray-700 shadow-md opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
      >
        {description}
      </span>
    </span>
  )
}

import { useCallback, useId, useLayoutEffect, useRef, useState } from 'react'
import { Info } from 'lucide-react'
import { cn } from '@/lib/utils'

type MetricInfoTooltipProps = {
  description: string
  className?: string
  /** Visually hidden label for assistive tech (defaults to description) */
  ariaLabel?: string
}

const TOOLTIP_MAX_W = 220
const VIEW_MARGIN = 8
const GAP_PX = 8

/**
 * Info trigger with a compact tooltip anchored to the icon (above, with arrow).
 * Uses fixed positioning + clamping so content stays in the viewport.
 */
export function MetricInfoTooltip({ description, className, ariaLabel }: MetricInfoTooltipProps) {
  const triggerRef = useRef<HTMLSpanElement>(null)
  const tooltipId = useId()
  const [open, setOpen] = useState(false)
  const [layout, setLayout] = useState({
    left: 0,
    top: 0,
    width: TOOLTIP_MAX_W,
    arrowLeft: TOOLTIP_MAX_W / 2,
  })

  const updatePosition = useCallback(() => {
    const el = triggerRef.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const maxW = Math.min(TOOLTIP_MAX_W, window.innerWidth - 2 * VIEW_MARGIN)
    const iconCenterX = r.left + r.width / 2
    let left = iconCenterX - maxW / 2
    left = Math.max(VIEW_MARGIN, Math.min(left, window.innerWidth - maxW - VIEW_MARGIN))
    const top = r.top - GAP_PX
    const arrowLeft = Math.max(12, Math.min(maxW - 12, iconCenterX - left))
    setLayout({ left, top, width: maxW, arrowLeft })
  }, [])

  const show = useCallback(() => {
    setOpen(true)
    requestAnimationFrame(() => updatePosition())
  }, [updatePosition])

  const hide = useCallback(() => setOpen(false), [])

  useLayoutEffect(() => {
    if (!open) return
    updatePosition()
    const onMove = () => updatePosition()
    window.addEventListener('resize', onMove)
    window.addEventListener('scroll', onMove, true)
    return () => {
      window.removeEventListener('resize', onMove)
      window.removeEventListener('scroll', onMove, true)
    }
  }, [open, updatePosition])

  return (
    <span className={cn('relative inline-flex shrink-0 items-center align-middle', className)}>
      <span
        ref={triggerRef}
        tabIndex={0}
        className={cn(
          'inline-flex cursor-help items-center justify-center rounded-sm p-0 text-gray-400 transition-colors',
          'hover:text-gray-600',
          'focus:outline-none focus-visible:text-gray-700',
          'focus-visible:ring-1 focus-visible:ring-gray-400/80 focus-visible:ring-offset-0'
        )}
        aria-label={ariaLabel ?? description}
        aria-describedby={open ? tooltipId : undefined}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
      >
        <Info className="size-4 shrink-0" strokeWidth={2} aria-hidden />
      </span>
      <span
        id={tooltipId}
        role="tooltip"
        style={{
          position: 'fixed',
          left: layout.left,
          top: layout.top,
          width: layout.width,
          transform: 'translateY(-100%)',
          zIndex: 200,
        }}
        className={cn(
          'pointer-events-none rounded-lg border border-gray-200 bg-white px-3 py-2 text-left text-xs leading-snug text-gray-700 shadow-lg transition-opacity duration-150',
          open ? 'opacity-100' : 'invisible opacity-0'
        )}
      >
        {description}
        <span
          className="pointer-events-none absolute -bottom-1 h-2 w-2 rotate-45 border border-gray-200 bg-white shadow-[1px_1px_0_0_rgba(0,0,0,0.04)]"
          style={{
            left: layout.arrowLeft,
            transform: 'translateX(-50%)',
          }}
          aria-hidden
        />
      </span>
    </span>
  )
}

import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, Clock, CheckCircle2 } from 'lucide-react'
import type { Session } from '@/types/session'
import type { TraineeSessionAnalytics } from '@/types/analytics'
import { cn } from '@/lib/utils'

const SPIKES_TOTAL_STAGES = 6

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0s'
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  if (m === 0) return `${s}s`
  if (s === 0) return `${m}m`
  return `${m}m ${s}s`
}

function clampStageCount(stageCount: number): number {
  if (!Number.isFinite(stageCount)) return 0
  return Math.max(0, Math.min(SPIKES_TOTAL_STAGES, Math.round(stageCount)))
}

function spikesStageCount(analytics: TraineeSessionAnalytics | undefined): number | null {
  if (!analytics) return null
  if (analytics.spikesStagesCovered?.length) return clampStageCount(analytics.spikesStagesCovered.length)
  const pct = analytics.spikesCoveragePercent
  if (typeof pct === 'number' && Number.isFinite(pct)) {
    return clampStageCount((pct / 100) * SPIKES_TOTAL_STAGES)
  }
  return null
}

function spikesCoveredLabel(analytics: TraineeSessionAnalytics | undefined): string {
  const count = spikesStageCount(analytics)
  if (count == null) return `— / ${SPIKES_TOTAL_STAGES}`
  return `${count} / ${SPIKES_TOTAL_STAGES}`
}

type SessionCardProps = {
  session: Session
  caseTitle: string
  analytics?: TraineeSessionAnalytics
  to?: string
  actions?: ReactNode
}

export function SessionCard({ session, caseTitle, analytics, to, actions }: SessionCardProps) {
  const isCompleted = session.state === 'completed'
  const empathyRounded =
    analytics && typeof analytics.empathyScore === 'number' ? Math.round(analytics.empathyScore) : null
  const spikesLabel = spikesCoveredLabel(analytics)
  const durationLabel = isCompleted ? formatDuration(session.durationSeconds ?? 0) : 'In progress'
  const stageLabel = session.currentSpikesStage
    ? session.currentSpikesStage.charAt(0).toUpperCase() + session.currentSpikesStage.slice(1)
    : null

  const row = (
    <div
      className={cn(
        'flex items-center justify-between p-4 border rounded-lg transition cursor-pointer',
        'hover:bg-gray-50 hover:border-gray-300'
      )}
    >
      <div className="flex items-center gap-4 min-w-0">
        <div
          className={cn(
            'h-9 w-9 flex shrink-0 items-center justify-center rounded-full',
            isCompleted ? 'bg-green-100 text-green-600' : 'bg-amber-100 text-amber-600'
          )}
        >
          {isCompleted ? <CheckCircle2 className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
        </div>

        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-base font-semibold text-gray-900 truncate">{caseTitle}</span>
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap',
                isCompleted ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
              )}
            >
              {isCompleted ? 'Completed' : 'Active'}
            </span>
            {stageLabel && (
              <span className="bg-purple-100 text-purple-700 text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap">
                {stageLabel}
              </span>
            )}
          </div>

          <div className="text-sm text-gray-500 mt-1">
            {formatDate(session.startedAt)} &bull; {durationLabel} &bull; Session #{session.id}
          </div>

          {isCompleted && analytics && (
            <div className="flex items-center gap-3 mt-1 text-sm">
              <span className="text-gray-500">
                Empathy{' '}
                <span className="font-semibold text-gray-700">{empathyRounded ?? '—'}%</span>
              </span>
              <span className="text-gray-300">&bull;</span>
              <span className="text-gray-500">
                SPIKES{' '}
                <span className="font-semibold text-gray-700">{spikesLabel}</span>
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0 ml-4">
        {actions}
        <ChevronRight className="h-5 w-5 text-gray-400" />
      </div>
    </div>
  )

  if (to) {
    return (
      <Link
        to={to}
        className="block no-underline"
        aria-label={`Open ${isCompleted ? 'feedback' : 'session'} for session ${session.id}`}
      >
        {row}
      </Link>
    )
  }

  return row
}

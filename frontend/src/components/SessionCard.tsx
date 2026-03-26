import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import type { Session } from '@/types/session'
import type { TraineeSessionAnalytics } from '@/types/analytics'
import { cn } from '@/lib/utils'

const SPIKES_TOTAL_STAGES = 6

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0s'
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  if (m === 0) return `${s}s`
  return `${m}m ${s}s`
}

function clampStageCount(stageCount: number): number {
  if (!Number.isFinite(stageCount)) return 0
  return Math.max(0, Math.min(SPIKES_TOTAL_STAGES, Math.round(stageCount)))
}

function empathyToneClass(score: number) {
  if (score >= 80) return 'text-emerald-700'
  if (score >= 60) return 'text-yellow-700'
  return 'text-red-700'
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

function performanceBadge(analytics: TraineeSessionAnalytics | undefined) {
  if (!analytics) return null
  const empathy = analytics.empathyScore
  const spikesCount = spikesStageCount(analytics) ?? 0

  const empathyMaster = empathy >= 85
  const strongSpikes = spikesCount >= 5

  if (empathyMaster && strongSpikes) return '🏅 Excellent Communication'
  if (empathyMaster) return '🏅 Empathy Master'
  if (strongSpikes) return '🏅 Strong SPIKES'
  return null
}

type SessionCardProps = {
  session: Session
  caseTitle: string
  analytics?: TraineeSessionAnalytics
  to: string
}

export function SessionCard({ session, caseTitle, analytics, to }: SessionCardProps) {
  const isCompleted = session.state === 'completed'

  const empathyRounded =
    analytics && typeof analytics.empathyScore === 'number' ? Math.round(analytics.empathyScore) : null

  const spikesLabel = spikesCoveredLabel(analytics)
  const badgeText = performanceBadge(analytics)

  const statusBadge = (
    <span
      className={cn(
        'px-3 py-1 text-[10px] font-semibold uppercase rounded-full border',
        isCompleted
          ? 'bg-gray-100 text-gray-600 border-gray-200'
          : 'bg-emerald-50 text-emerald-700 border-emerald-200'
      )}
    >
      {isCompleted ? 'Completed' : 'Active'}
    </span>
  )

  const durationLabel = isCompleted ? formatDuration(session.durationSeconds ?? 0) : 'In progress'

  return (
    <Link
      to={to}
      className="group block no-underline"
      aria-label={`Open ${isCompleted ? 'feedback' : 'session'} for session ${session.id}`}
    >
      <Card
        className={cn(
          'h-full transition-colors',
          'py-4 hover:bg-gray-50 cursor-pointer',
          'border border-gray-200'
        )}
      >
        <CardContent className="p-0">
          <div className="flex flex-col gap-3 px-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-base font-semibold text-gray-900 truncate">{caseTitle}</div>
              </div>
              {statusBadge}
            </div>

            <div className="flex items-center gap-3 text-sm text-gray-500">
              <span>{formatDate(session.startedAt)}</span>
              <span className="text-gray-300">•</span>
              <span>{durationLabel}</span>
              <span className="text-gray-300">•</span>
              <span>Session #{session.id}</span>
            </div>

            {isCompleted && (
              <div className="flex items-center justify-start gap-3">
                <div className={cn('text-sm font-semibold', empathyToneClass(analytics?.empathyScore ?? 0))}>
                  Empathy {empathyRounded ?? '—'}
                </div>
                <span className="text-gray-300">•</span>
                <div className="text-sm font-medium text-purple-700">
                  SPIKES {spikesLabel}
                </div>
              </div>
            )}

            {isCompleted && badgeText && (
              <div className="pt-1 text-sm font-semibold text-gray-700">{badgeText}</div>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}


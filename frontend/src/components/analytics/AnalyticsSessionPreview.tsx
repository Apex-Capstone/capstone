import type { TraineeSessionAnalytics } from '@/types/analytics'
import { formatPercentWhole } from '@/utils/format'

/** Canonical SPIKES stage order for display (matches backend scoring). */
const SPIKES_STAGE_ORDER = ['S', 'P', 'I', 'K', 'E', 'S2'] as const

const SPIKES_STAGE_HINT: Record<string, string> = {
  S: 'Setting up the conversation',
  P: 'Perception / invitation to share',
  I: 'Invitation to share information',
  K: 'Knowledge',
  E: 'Empathy with emotions',
  S2: 'Strategy / summary',
}

function sortSpikeStages(stages: string[]): string[] {
  return [...stages].sort((a, b) => {
    const ia = SPIKES_STAGE_ORDER.indexOf(a as (typeof SPIKES_STAGE_ORDER)[number])
    const ib = SPIKES_STAGE_ORDER.indexOf(b as (typeof SPIKES_STAGE_ORDER)[number])
    if (ia === -1 && ib === -1) return a.localeCompare(b)
    if (ia === -1) return 1
    if (ib === -1) return -1
    return ia - ib
  })
}

function formatSessionDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '—'
  const total = Math.floor(seconds)
  const mins = Math.floor(total / 60)
  const secs = total % 60
  if (mins >= 60) {
    const h = Math.floor(mins / 60)
    const m = mins % 60
    return `${h}h ${m}m`
  }
  if (mins > 0) return `${mins}m ${secs}s`
  return `${secs}s`
}

function formatCompletedAt(iso: string): string {
  const t = Date.parse(iso)
  if (!Number.isFinite(t)) return '—'
  return new Date(t).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

type AnalyticsSessionPreviewProps = {
  session: TraineeSessionAnalytics
}

/**
 * Compact trainee-facing summary for an analytics table row (full detail remains on /feedback).
 */
export function AnalyticsSessionPreview({ session }: AnalyticsSessionPreviewProps) {
  const eo =
    typeof session.eoAddressedRate === 'number' && Number.isFinite(session.eoAddressedRate)
      ? formatPercentWhole(session.eoAddressedRate)
      : null

  const stages =
    session.spikesStagesCovered && session.spikesStagesCovered.length > 0
      ? sortSpikeStages(session.spikesStagesCovered)
      : null

  return (
    <div className="border-l-2 border-blue-200 pl-4 text-sm text-gray-800">
      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Completed</dt>
          <dd className="mt-0.5 text-gray-900">{formatCompletedAt(session.createdAt)}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Duration</dt>
          <dd className="mt-0.5 text-gray-900">{formatSessionDuration(session.durationSeconds)}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Case</dt>
          <dd className="mt-0.5 line-clamp-2 text-gray-900" title={session.caseTitle}>
            {session.caseTitle}
          </dd>
        </div>
        {eo != null && (
          <div className="sm:col-span-2 lg:col-span-1">
            <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Empathy opportunities addressed
            </dt>
            <dd className="mt-0.5 text-gray-900">{eo}</dd>
          </div>
        )}
      </dl>

      <div className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t border-gray-100 pt-3 text-xs text-gray-600">
        <span>
          SPIKES coverage <strong className="font-semibold text-gray-900">{formatPercentWhole(session.spikesCoveragePercent)}</strong>
        </span>
        <span className="text-gray-300" aria-hidden>
          ·
        </span>
        <span>
          SPIKES completion{' '}
          <strong className="font-semibold text-gray-900">{formatPercentWhole(session.spikesCompletionScore)}</strong>
        </span>
      </div>

      {stages != null && (
        <div className="mt-3">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">SPIKES stages in this session</p>
          <ul className="mt-1.5 flex flex-wrap gap-1.5" aria-label="SPIKES stages covered">
            {stages.map((code) => (
              <li key={code}>
                <span
                  className="inline-flex items-center rounded-md border border-gray-200 bg-white px-2 py-0.5 text-xs font-medium text-gray-800 shadow-sm"
                  title={SPIKES_STAGE_HINT[code] ?? `Stage ${code}`}
                >
                  {code}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-3 text-xs text-gray-500">
        Open <span className="font-medium text-gray-700">View feedback</span> for the full report and conversation
        detail.
      </p>
    </div>
  )
}

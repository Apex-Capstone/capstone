import type { Turn } from '@/types/session'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface FeedbackConversationTimelineProps {
  turns: Turn[]
}

type MetricsBadges = {
  labels: string[]
}

const parseMetricsBadges = (metricsJson?: string): MetricsBadges => {
  if (!metricsJson) {
    return { labels: [] }
  }

  try {
    // metrics_json is stored as a JSON string; backend is tolerant of both proper JSON
    // and stringified dictionaries. We mirror that robustness client-side.
    const raw =
      typeof metricsJson === 'string'
        ? JSON.parse(metricsJson)
        : metricsJson

    const labels: string[] = []

    if (!raw || typeof raw !== 'object') {
      return { labels }
    }

    // Heuristics for common scoring flags – these align with likely fields from scoring_service.
    const empathyDetected =
      raw.empathy_detected === true ||
      raw.empathy === 'detected' ||
      raw.empathy?.detected === true ||
      (Array.isArray(raw.tags) && raw.tags.includes('empathy'))

    const openQuestion =
      raw.open_question === true ||
      raw.question_type === 'open' ||
      raw.question?.type === 'open'

    const tone = raw.tone || raw.speech_tone || raw.voice_tone

    if (empathyDetected) {
      labels.push('Empathy detected')
    }

    if (openQuestion) {
      labels.push('Open question')
    }

    if (tone === 'calm') {
      labels.push('Calm tone')
    }

    // Generic fallback: expose any additional boolean tags as simple labels
    if (raw.flags && typeof raw.flags === 'object') {
      Object.entries(raw.flags as Record<string, unknown>).forEach(([key, value]) => {
        if (value === true) {
          labels.push(key.replace(/_/g, ' '))
        }
      })
    }

    return { labels }
  } catch {
    return { labels: [] }
  }
}

const formatRoleLabel = (role: string): 'Doctor' | 'Patient' => {
  const normalized = role.toLowerCase()
  if (['user', 'trainee', 'doctor', 'physician', 'clinician'].includes(normalized)) {
    return 'Doctor'
  }
  return 'Patient'
}

const mapRoleToSide = (role: string): 'left' | 'right' => {
  const normalized = role.toLowerCase()
  if (['user', 'trainee', 'doctor', 'physician', 'clinician'].includes(normalized)) {
    return 'right'
  }
  return 'left'
}

export const FeedbackConversationTimeline = ({
  turns,
}: FeedbackConversationTimelineProps) => {
  const sortedTurns = [...turns].sort((a, b) => a.turnNumber - b.turnNumber)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Conversation Timeline</CardTitle>
      </CardHeader>
      <CardContent>
        {sortedTurns.length === 0 ? (
          <p className="text-sm text-gray-500">No conversation turns recorded for this session.</p>
        ) : (
          <div className="space-y-4">
            {sortedTurns.map((turn) => {
              const roleLabel = formatRoleLabel(turn.role)
              const side = mapRoleToSide(turn.role)
              const spikesStage = turn.spikesStage ?? '—'
              const { labels: metricBadges } = parseMetricsBadges(turn.metricsJson)

              return (
                <div
                  key={turn.id}
                  className={cn(
                    'flex w-full items-start gap-3',
                    side === 'right' ? 'justify-end' : 'justify-start'
                  )}
                >
                  {side === 'left' && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-xs font-semibold text-emerald-700">
                      {roleLabel[0]}
                    </div>
                  )}

                  <div
                    className={cn(
                      'max-w-[80%] rounded-lg px-4 py-3 shadow-sm',
                      side === 'right'
                        ? 'bg-emerald-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    )}
                  >
                    <div className="mb-1 flex flex-wrap items-center gap-2 text-xs">
                      <span
                        className={cn(
                          'font-semibold',
                          side === 'right' ? 'text-emerald-50' : 'text-gray-700'
                        )}
                      >
                        {roleLabel}
                      </span>
                      <span className="rounded-full bg-orange-50 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-orange-700">
                        {spikesStage}
                      </span>
                      <span
                        className={cn(
                          'ml-auto text-[10px]',
                          side === 'right' ? 'text-emerald-100' : 'text-gray-500'
                        )}
                      >
                        {new Date(turn.timestamp).toLocaleTimeString()}
                      </span>
                    </div>

                    <p className="text-sm whitespace-pre-wrap">{turn.text}</p>

                    {metricBadges.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {metricBadges.map((badge) => (
                          <span
                            key={badge}
                            className={cn(
                              'rounded-full px-2 py-0.5 text-[10px] font-medium',
                              side === 'right'
                                ? 'bg-emerald-500/80 text-emerald-50'
                                : 'bg-gray-200 text-gray-700'
                            )}
                          >
                            {badge}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {side === 'right' && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-200 text-xs font-semibold text-gray-700">
                      {roleLabel[0]}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}


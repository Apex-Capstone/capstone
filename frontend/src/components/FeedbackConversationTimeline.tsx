/**
 * Conversation transcript with per-turn SPIKES labels, metric badges, and empathy span highlights.
 */
import type React from 'react'
import type { Turn } from '@/types/session'
import type { Feedback } from '@/api/feedback.api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

/** Props for {@link FeedbackConversationTimeline}. */
interface FeedbackConversationTimelineProps {
  turns: Turn[]
  feedback: Feedback
}

/** Parsed heuristic labels derived from `metrics_json`. */
type MetricsBadges = {
  labels: string[]
}

/** Normalized text span for underline rendering. */
type Span = {
  id?: string | number
  span_type?: string
  start: number
  end: number
}

/**
 * Parses `metrics_json` into human-readable badge strings (empathy, questions, tone).
 *
 * @param metricsJson - JSON string or undefined from a turn
 * @returns Collected label strings for chips
 */
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
    const voiceToneLabels = Array.isArray(raw.voice_tone?.labels)
      ? raw.voice_tone.labels.filter(
          (label: unknown): label is string =>
            typeof label === 'string' && label.toLowerCase() !== 'unclear'
        )
      : []

    if (empathyDetected) {
      labels.push('Empathy detected')
    }

    if (openQuestion) {
      labels.push('Open question')
    }

    if (tone === 'calm') {
      labels.push('Calm tone')
    }
    if (tone && typeof tone === 'object') {
      if (tone.calm === true) labels.push('Calm tone')
      if (tone.clear === true) labels.push('Clear delivery')
    }
    if (
      typeof raw.voice_tone?.primary === 'string' &&
      raw.voice_tone.primary.toLowerCase() !== 'unclear'
    ) {
      labels.push(`Voice: ${raw.voice_tone.primary}`)
    }
    voiceToneLabels.slice(0, 2).forEach((label: string) => labels.push(`Voice: ${label}`))

    // Generic fallback: expose any additional boolean tags as simple labels
    if (raw.flags && typeof raw.flags === 'object') {
      Object.entries(raw.flags as Record<string, unknown>).forEach(([key, value]) => {
        if (value === true) {
          labels.push(key.replace(/_/g, ' '))
        }
      })
    }

    return { labels: [...new Set(labels)] }
  } catch {
    return { labels: [] }
  }
}

/**
 * Maps backend role strings to a display label for the transcript.
 *
 * @param role - Raw role from the turn
 * @returns Doctor or Patient
 */
const formatRoleLabel = (role: string): 'Doctor' | 'Patient' => {
  const normalized = role.toLowerCase()
  if (['user', 'trainee', 'doctor', 'physician', 'clinician'].includes(normalized)) {
    return 'Doctor'
  }
  return 'Patient'
}

/**
 * Places clinician turns on the right and patient on the left (chat layout).
 *
 * @param role - Raw role from the turn
 * @returns Horizontal alignment side
 */
const mapRoleToSide = (role: string): 'left' | 'right' => {
  const normalized = role.toLowerCase()
  if (['user', 'trainee', 'doctor', 'physician', 'clinician'].includes(normalized)) {
    return 'right'
  }
  return 'left'
}

type EmpathyMarkerType = 'empathy_response' | 'empathy_opportunity' | 'missed_opportunity'

type EmpathyMarkersByTurn = Record<
  number,
  {
    types: EmpathyMarkerType[]
  }
>

/**
 * Finds the next clinician turn after a given turn number.
 *
 * @param turns - Full ordered transcript
 * @param afterTurnNumber - EO turn number
 * @returns Next clinician turn number, if present
 */
const getNextClinicianTurnNumber = (
  turns: Array<Turn & { spansJson?: string }>,
  afterTurnNumber: number,
): number | undefined => {
  return turns
    .filter((turn) => turn.turnNumber > afterTurnNumber)
    .sort((a, b) => a.turnNumber - b.turnNumber)
    .find((turn) =>
      ['user', 'trainee', 'doctor', 'physician', 'clinician'].includes(turn.role.toLowerCase())
    )?.turnNumber
}

/**
 * Parses `spans_json` into validated start/end spans for highlighting.
 *
 * @param spansJson - JSON string or parsed array
 * @returns Sorted valid spans
 */
const parseSpans = (spansJson?: unknown): Span[] => {
  if (!spansJson) return []

  try {
    const raw =
      typeof spansJson === 'string'
        ? JSON.parse(spansJson)
        : spansJson

    if (!Array.isArray(raw)) {
      return []
    }

    // Normalise into internal Span shape, supporting both start/end and start_char/end_char.
    return raw
      .map((s: any): Span | null => {
        if (!s) return null

        const start: number =
          typeof s.start === 'number'
            ? s.start
            : typeof s.start_char === 'number'
            ? s.start_char
            : -1
        const end: number =
          typeof s.end === 'number'
            ? s.end
            : typeof s.end_char === 'number'
            ? s.end_char
            : -1

        if (start < 0 || end <= start) {
          return null
        }

        return {
          id: s.id ?? s.span_id,
          span_type: s.span_type,
          start,
          end,
        }
      })
      .filter((s: Span | null): s is Span => s !== null)
  } catch {
    return []
  }
}

/**
 * Builds per-turn empathy marker flags from span types and missed-opportunity summaries.
 *
 * @param feedback - Session feedback containing link maps and missed rows
 * @param turns - Turns with optional `spansJson`
 * @returns Map of turn number to marker type list
 */
const buildEmpathyTimelineMarkers = (
  feedback: Feedback,
  turns: Array<Turn & { spansJson?: string }>,
): EmpathyMarkersByTurn => {
  const markers: EmpathyMarkersByTurn = {}

  if (!feedback || !Array.isArray(turns) || turns.length === 0) {
    return markers
  }

  // 1) Per-turn markers based on span types (eo / response / elicitation)
  turns.forEach((turn) => {
    const spans = parseSpans(turn.spansJson)
    if (!spans.length) {
      return
    }

    const tn = turn.turnNumber
    if (!markers[tn]) {
      markers[tn] = { types: [] }
    }

    if (
      spans.some(
        (s) =>
          s.span_type === 'eo' ||
          s.span_type === 'empathy_opportunity' ||
          s.span_type === 'eo_missed',
      )
    ) {
      if (!markers[tn].types.includes('empathy_opportunity')) {
        markers[tn].types.push('empathy_opportunity')
      }
    }

    if (
      spans.some(
        (s) =>
          s.span_type === 'response' ||
          s.span_type === 'empathy_response',
      )
    ) {
      if (!markers[tn].types.includes('empathy_response')) {
        markers[tn].types.push('empathy_response')
      }
    }
  })

  // 2) Overlay missed opportunities using backend summary (has turn_number)
  if (Array.isArray(feedback.missed_opportunities)) {
    feedback.missed_opportunities.forEach((entry) => {
      const eoTurnNumber = typeof (entry as any)?.turn_number === 'number'
        ? (entry as any).turn_number
        : undefined
      if (!eoTurnNumber) return

      const clinicianTurnNumber = getNextClinicianTurnNumber(turns, eoTurnNumber)

      if (!markers[eoTurnNumber]) {
        markers[eoTurnNumber] = { types: [] }
      }
      if (!markers[eoTurnNumber].types.includes('empathy_opportunity')) {
        markers[eoTurnNumber].types.push('empathy_opportunity')
      }

      const missedMarkerTurn = clinicianTurnNumber ?? eoTurnNumber
      if (!markers[missedMarkerTurn]) {
        markers[missedMarkerTurn] = { types: [] }
      }
      if (!markers[missedMarkerTurn].types.includes('missed_opportunity')) {
        markers[missedMarkerTurn].types.push('missed_opportunity')
      }
    })
  }

  return markers
}

/**
 * Splits turn text and injects underlined spans for EO/response/missed/elicitation styling.
 *
 * @param text - Full turn text
 * @param spansJson - Optional spans payload
 * @param feedback - Used for link maps and missed id sets
 * @returns Plain string or array of text/React nodes
 */
const renderTextWithSpans = (
  text: string,
  spansJson: string | undefined,
  feedback: Feedback,
) => {
  const spans = parseSpans(spansJson)
  if (spans.length === 0) {
    return text
  }

  const eoSpanIds = new Set<string>()
  const responseSpanIds = new Set<string>()
  const missedSpanIds = new Set<string>((feedback.missed_opportunities ?? []).map(String))

  if (feedback.eo_to_response_links && typeof feedback.eo_to_response_links === 'object') {
    Object.entries(feedback.eo_to_response_links).forEach(
      ([eoSpanId, links]: [string, unknown]) => {
        eoSpanIds.add(String(eoSpanId))
        if (Array.isArray(links)) {
          ;(links as any[]).forEach((link) => {
            if (link?.target_span_id) {
              responseSpanIds.add(String(link.target_span_id))
            }
          })
        }
      },
    )
  }

  const pieces: Array<string | React.ReactNode> = []
  let cursor = 0

  const sorted = [...spans].sort((a, b) => a.start - b.start)

  sorted.forEach((span, index) => {
    if (span.start < cursor) {
      return
    }

    if (span.start > cursor) {
      pieces.push(text.slice(cursor, span.start))
    }

    const spanText = text.slice(span.start, span.end)

    let className = ''
    const spanId = span.id != null ? String(span.id) : undefined
    const spanType = span.span_type ?? ''

    // Priority: missed > EO > response, using either backend IDs or span_type hints
    const isMissed =
      (spanId && missedSpanIds.has(spanId)) || spanType === 'eo_missed' || spanType === 'missed'
    const isEo =
      (spanId && eoSpanIds.has(spanId)) ||
      spanType === 'eo' ||
      spanType === 'empathy_opportunity'
    const isResponse =
      (spanId && responseSpanIds.has(spanId)) ||
      spanType === 'response' ||
      spanType === 'empathy_response'
    const isElicitation = spanType === 'elicitation'

    if (isMissed) {
      className = 'underline decoration-red-400 decoration-2 underline-offset-2'
    } else if (isEo) {
      className = 'underline decoration-amber-400 decoration-2 underline-offset-2'
    } else if (isResponse) {
      className = 'underline decoration-apex-400 decoration-2 underline-offset-2'
    } else if (isElicitation) {
      className = 'underline decoration-apex-600 decoration-2 underline-offset-2'
    }

    pieces.push(
      <span
        key={`span-${index}`}
        className={className}
        title={
          isMissed
            ? 'Missed empathy opportunity'
            : isEo
            ? 'Empathy opportunity detected'
            : isResponse
            ? 'Empathic response'
            : isElicitation
            ? 'Elicitation question'
            : undefined
        }
      >
        {spanText}
      </span>,
    )

    cursor = span.end
  })

  if (cursor < text.length) {
    pieces.push(text.slice(cursor))
  }

  return pieces
}

/**
 * Full conversation analysis card: sorted turns with empathy overlays and metric chips.
 *
 * @param props - {@link FeedbackConversationTimelineProps}
 * @returns Card with transcript timeline
 */
export const FeedbackConversationTimeline = ({
  turns,
  feedback,
}: FeedbackConversationTimelineProps) => {
  const sortedTurns = [...turns].sort((a, b) => a.turnNumber - b.turnNumber)
  const empathyMarkers = buildEmpathyTimelineMarkers(feedback, sortedTurns)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Conversation Analysis</CardTitle>
      </CardHeader>
      <CardContent>
        {sortedTurns.length === 0 ? (
          <p className="text-sm text-gray-500">No conversation turns recorded for this session.</p>
        ) : (
          <div className="h-[32rem] space-y-4 overflow-y-auto pr-2">
            {sortedTurns.map((turn) => {
              const roleLabel = formatRoleLabel(turn.role)
              const side = mapRoleToSide(turn.role)
              const spikesStage = turn.spikesStage ?? '—'
              const { labels: metricBadges } = parseMetricsBadges(turn.metricsJson)
              const markersForTurn = empathyMarkers[turn.turnNumber]

              return (
                <div
                  key={turn.id}
                  className={cn(
                    'flex w-full items-start gap-3',
                    side === 'right' ? 'justify-end' : 'justify-start'
                  )}
                >
                  {side === 'left' && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-apex-100 text-xs font-semibold text-apex-700">
                      {roleLabel[0]}
                    </div>
                  )}

                  <div
                    className={cn(
                      'max-w-[80%] rounded-lg px-4 py-3 shadow-sm',
                      side === 'right'
                        ? 'bg-apex-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    )}
                  >
                    <div className="mb-1 flex flex-wrap items-center gap-2 text-xs">
                      <span
                        className={cn(
                          'font-semibold',
                          side === 'right' ? 'text-apex-50' : 'text-gray-700'
                        )}
                      >
                        {roleLabel}
                      </span>
                      {side === 'right' && (
                        <span className="rounded-full bg-orange-50 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-orange-700">
                          {spikesStage}
                        </span>
                      )}
                      <span
                        className={cn(
                          'ml-auto text-[10px]',
                          side === 'right' ? 'text-apex-100' : 'text-gray-500'
                        )}
                      >
                        {new Date(turn.timestamp).toLocaleTimeString()}
                      </span>
                    </div>

                    <p className="text-sm whitespace-pre-wrap">
                      {renderTextWithSpans(turn.text, turn.spansJson, feedback)}
                    </p>

                    {markersForTurn && markersForTurn.types.length > 0 && (
                      <div className="mt-2 space-y-1 text-xs">
                        {markersForTurn.types.includes('empathy_opportunity') && (
                          <div className="font-medium text-amber-500">
                            ⚠ Empathy Opportunity
                          </div>
                        )}
                        {markersForTurn.types.includes('missed_opportunity') && (
                          <div
                            className={cn(
                              'inline-flex rounded-full px-2 py-1 font-medium',
                              side === 'right'
                                ? 'bg-amber-50 text-amber-700'
                                : 'bg-amber-100 text-amber-700'
                            )}
                          >
                            ⚠ Missed Empathy Opportunity
                          </div>
                        )}
                        {markersForTurn.types.includes('empathy_response') && (
                          <div className="font-medium text-apex-400">
                            ✓ Empathy Response
                          </div>
                        )}
                      </div>
                    )}

                    {metricBadges.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {metricBadges.map((badge) => (
                          <span
                            key={badge}
                            className={cn(
                              'rounded-full px-2 py-0.5 text-[10px] font-medium',
                              side === 'right'
                                ? 'bg-apex-500/80 text-apex-50'
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


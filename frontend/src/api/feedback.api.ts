/**
 * Session feedback API: loads evaluator output and normalizes `snake_case` into the UI model.
 */
import api from '@/api/client'

/** SPIKES stage coverage summary for charts and progress UI. */
export interface SpikesCoverage {
  setting: boolean
  perception: boolean
  invitation: boolean
  knowledge: boolean
  emotions: boolean
  strategy: boolean
  coveredCount: number
  total: number
   covered: string[]
   percent: number
}

/** Link between empathy-opportunity spans in feedback graphs. */
export interface EmpathyLink {
  source_span_id: string
  target_span_id: string
  relation_type: string
  confidence: number
}

/**
 * Rich feedback record for the Feedback page (scores, SPIKES, EO stats, optional raw snake_case passthrough).
 */
export interface Feedback {
  id: number
  sessionId: number

  empathyScore: number
  spikesCompletionScore: number
  overallScore: number

  eoCountsByDimension?: {
    Feeling: { explicit: number; implicit: number }
    Judgment: { explicit: number; implicit: number }
    Appreciation: { explicit: number; implicit: number }
  }
  elicitationCountsByType?: {
    direct: { Feeling: number; Judgment: number; Appreciation: number }
    indirect: { Feeling: number; Judgment: number; Appreciation: number }
  }
  responseCountsByType?: {
    understanding: number
    sharing: number
    acceptance: number
  }

  linkageStats?: {
    total_eos: number
    addressed_count: number
    missed_count: number
    addressed_rate: number
    missed_rate: number
  }
  missedOpportunitiesByDimension?: {
    Feeling: number
    Judgment: number
    Appreciation: number
  }

  spikesCoverage?: SpikesCoverage
  spikesTimestamps?: Record<string, { start_ts: string; end_ts: string }>
  spikesStrategies?: Record<string, Array<{ strategy: string; turn: number }>>

  questionBreakdown?: {
    open: number
    closed: number
    eliciting: number
    ratio_open: number
  }

  latencyMsAvg: number

  /** Raw JSON from the scoring pipeline (phase, hybrid LLM merge, rule scores, etc.). */
  evaluatorMeta?: Record<string, unknown> | null

  strengths?: string | null
  areasForImprovement?: string | null
  detailedFeedback?: string | null

  createdAt: string
  eo_to_response_links?: Record<string, EmpathyLink[]>
  eo_to_elicitation_links?: Record<string, EmpathyLink[]>
  missed_opportunities?: Array<Record<string, unknown>>
  eo_counts_by_dimension?: Record<string, unknown>
  spikes_strategies?: Record<string, unknown>
}

/**
 * Loads feedback for a session and maps API fields into {@link Feedback}.
 *
 * @remarks
 * Normalizes `spikes_coverage` (including abbreviated letter codes) into {@link SpikesCoverage}.
 * Passes through optional snake_case fields for components that still read raw API keys.
 *
 * @param sessionId - Session id (string for route param compatibility)
 * @returns Fully shaped {@link Feedback} for the UI
 */
export const fetchFeedback = async (sessionId: string): Promise<Feedback> => {
  const { data } = await api.get(`/v1/sessions/${sessionId}/feedback`)

  // Map snake_case API response into the richer Feedback model used by the UI
  let spikesCoverage: SpikesCoverage | undefined

  if (data.spikes_coverage && typeof data.spikes_coverage === 'object') {
    const coveredRaw = Array.isArray(data.spikes_coverage.covered)
      ? data.spikes_coverage.covered
      : []

    const normalizedCovered = coveredRaw
      .map((s: unknown) => (typeof s === 'string' ? s.toLowerCase() : ''))
      .filter(Boolean)

    const setting =
      normalizedCovered.includes('setting') || normalizedCovered.includes('s')
    const perception =
      normalizedCovered.includes('perception') || normalizedCovered.includes('p')
    const invitation =
      normalizedCovered.includes('invitation') || normalizedCovered.includes('i')
    const knowledge =
      normalizedCovered.includes('knowledge') || normalizedCovered.includes('k')
    const emotions =
      normalizedCovered.includes('emotion') ||
      normalizedCovered.includes('emotions') ||
      normalizedCovered.includes('e')
    const strategy =
      normalizedCovered.includes('strategy') || normalizedCovered.includes('s2')

    const stages = { setting, perception, invitation, knowledge, emotions, strategy }
    const coveredCount = Object.values(stages).filter(Boolean).length
    const total = 6

    const percent =
      typeof data.spikes_coverage.percent === 'number'
        ? data.spikes_coverage.percent
        : total > 0
          ? coveredCount / total
          : 0

    spikesCoverage = {
      ...stages,
      coveredCount,
      total,
      covered: normalizedCovered,
      percent,
    }
  }

  return {
    id: data.id,
    sessionId: data.session_id,
    empathyScore: data.empathy_score ?? 0,
    spikesCompletionScore: data.spikes_completion_score ?? 0,
    overallScore: data.overall_score ?? 0,
    eoCountsByDimension: data.eo_counts_by_dimension ?? undefined,
    elicitationCountsByType: data.elicitation_counts_by_type ?? undefined,
    responseCountsByType: data.response_counts_by_type ?? undefined,
    linkageStats: data.linkage_stats ?? undefined,
    missedOpportunitiesByDimension: data.missed_opportunities_by_dimension ?? undefined,
    spikesCoverage,
    spikesTimestamps: data.spikes_timestamps ?? undefined,
    spikesStrategies: data.spikes_strategies ?? undefined,
    questionBreakdown: data.question_breakdown ?? undefined,
    latencyMsAvg: data.latency_ms_avg ?? 0,
    evaluatorMeta:
      data.evaluator_meta != null && typeof data.evaluator_meta === 'object'
        ? (data.evaluator_meta as Record<string, unknown>)
        : null,
    strengths: data.strengths ?? null,
    areasForImprovement: data.areas_for_improvement ?? null,
    detailedFeedback: data.detailed_feedback ?? null,
    createdAt: data.created_at,
    eo_to_response_links: data.eo_to_response_links ?? undefined,
    eo_to_elicitation_links: data.eo_to_elicitation_links ?? undefined,
    missed_opportunities: data.missed_opportunities ?? undefined,
    eo_counts_by_dimension: data.eo_counts_by_dimension ?? undefined,
    spikes_strategies: data.spikes_strategies ?? undefined,
  }
}

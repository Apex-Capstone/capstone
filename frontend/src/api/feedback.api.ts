import api from '@/api/client'

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

  spikesCoverage?: {
    covered: string[]
    percent: number
  }
  spikesTimestamps?: Record<string, { start_ts: string; end_ts: string }>
  spikesStrategies?: Record<string, Array<{ strategy: string; turn: number }>>

  questionBreakdown?: {
    open: number
    closed: number
    eliciting: number
    ratio_open: number
  }

  latencyMsAvg: number

  strengths?: string | null
  areasForImprovement?: string | null
  detailedFeedback?: string | null

  createdAt: string
}

function mapSnakeToCamel(data: Record<string, any>): Feedback {
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
    spikesCoverage: data.spikes_coverage ?? undefined,
    spikesTimestamps: data.spikes_timestamps ?? undefined,
    spikesStrategies: data.spikes_strategies ?? undefined,
    questionBreakdown: data.question_breakdown ?? undefined,
    latencyMsAvg: data.latency_ms_avg ?? 0,
    strengths: data.strengths ?? null,
    areasForImprovement: data.areas_for_improvement ?? null,
    detailedFeedback: data.detailed_feedback ?? null,
    createdAt: data.created_at,
  }
}

export const fetchFeedback = async (sessionId: string): Promise<Feedback> => {
  const { data } = await api.get(`/v1/sessions/${sessionId}/feedback`)
  return mapSnakeToCamel(data)
}

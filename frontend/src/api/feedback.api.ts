import api from '@/api/client'

export interface SpikesCoverage {
  setting: boolean
  perception: boolean
  invitation: boolean
  knowledge: boolean
  emotions: boolean
  strategy: boolean
  coveredCount: number
  total: number
}

export interface EmpathyLink {
  source_span_id: string
  target_span_id: string
  relation_type: string
  confidence: number
}

export interface Feedback {
  sessionId: string
  caseId: string
  overallScore: number
  strengths: string[]
  areasForImprovement: string[]
  recommendations: string[]
  metrics: {
    communication: number
    clinicalReasoning: number
    empathy: number
    professionalism: number
  }
  createdAt: string
  spikesCoverage?: SpikesCoverage
  conversationMetrics?: {
    empathyScore: number
    openQuestionRatio: number
  }
  dialogueExamples?: {
    strong: Array<{ text: string; context: string }>
    weak: Array<{ text: string; context: string; improvement: string }>
  }
  eo_to_response_links?: Record<string, EmpathyLink[]>
  eo_to_elicitation_links?: Record<string, EmpathyLink[]>
  missed_opportunities?: Array<Record<string, unknown>>
  eo_counts_by_dimension?: Record<string, unknown>
  spikes_strategies?: Record<string, unknown>
}

export const fetchFeedback = async (sessionId: string): Promise<Feedback> => {
  const { data } = await api.get(`/v1/sessions/${sessionId}/feedback`)

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

    spikesCoverage = {
      ...stages,
      coveredCount,
      total: 6,
    }
  }

  return {
    sessionId: String(data.session_id),
    caseId: data.case_id != null ? String(data.case_id) : '',
    overallScore: data.overall_score ?? 0,
    strengths: data.strengths
      ? typeof data.strengths === 'string'
        ? data.strengths.split('\n')
        : [data.strengths]
      : [],
    areasForImprovement: data.areas_for_improvement
      ? typeof data.areas_for_improvement === 'string'
        ? data.areas_for_improvement.split('\n')
        : [data.areas_for_improvement]
      : [],
    recommendations: [],
    metrics: {
      communication: data.communication_score ?? 0,
      clinicalReasoning: data.clinical_reasoning_score ?? 0,
      empathy: data.empathy_score ?? 0,
      professionalism: data.professionalism_score ?? 0,
    },
    createdAt: data.created_at ?? new Date().toISOString(),
    spikesCoverage,
    conversationMetrics:
      data.question_breakdown != null
        ? {
            empathyScore: data.empathy_score ?? 0,
            openQuestionRatio: data.question_breakdown.ratio_open ?? 0,
          }
        : undefined,
    dialogueExamples: undefined,
    eo_to_response_links: data.eo_to_response_links ?? undefined,
    eo_to_elicitation_links: data.eo_to_elicitation_links ?? undefined,
    missed_opportunities: data.missed_opportunities ?? undefined,
    eo_counts_by_dimension: data.eo_counts_by_dimension ?? undefined,
    spikes_strategies: data.spikes_strategies ?? undefined,
  }
}

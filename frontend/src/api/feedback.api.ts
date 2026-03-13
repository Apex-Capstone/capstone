import api from '@/api/client'

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
  spikesMetrics?: {
    setting: number
    perception: number
    invitation: number
    knowledge: number
    emotions: number
    strategy: number
  }
  conversationMetrics?: {
    empathyScore: number
    openQuestionRatio: number
  }
  dialogueExamples?: {
    strong: Array<{ text: string; context: string }>
    weak: Array<{ text: string; context: string; improvement: string }>
  }
}

export const fetchFeedback = async (sessionId: string): Promise<Feedback> => {
  const { data } = await api.get(`/v1/sessions/${sessionId}/feedback`)

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
    spikesMetrics: data.spikes_coverage
      ? {
          setting: 0,
          perception: 0,
          invitation: 0,
          knowledge: 0,
          emotions: 0,
          strategy: 0,
        }
      : undefined,
    conversationMetrics:
      data.question_breakdown != null
        ? {
            empathyScore: data.empathy_score ?? 0,
            openQuestionRatio: data.question_breakdown.ratio_open ?? 0,
          }
        : undefined,
    dialogueExamples: undefined,
  }
}

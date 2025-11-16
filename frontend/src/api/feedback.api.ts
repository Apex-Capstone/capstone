import api from '@/api/client'

// If you already have a shared type, import it instead of redeclaring.
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

// Real endpoint (adjust path if your BE differs)
export const fetchFeedback = async (sessionId: string): Promise<Feedback> => {
  try {
    const { data } = await api.get(`/v1/feedback/${sessionId}`)
    return data
  } catch (e) {
    // Optional: dev fallback if BE isn’t implemented yet
    console.warn('[fetchFeedback] falling back to mock:', e)
    return {
      sessionId,
      caseId: '1',
      overallScore: 85,
      strengths: ['Excellent use of empathetic language'],
      areasForImprovement: ['Could have explored emotions more deeply'],
      recommendations: ['Practice Ask–Tell–Ask'],
      metrics: {
        communication: 88,
        clinicalReasoning: 82,
        empathy: 80,
        professionalism: 90,
      },
      createdAt: new Date().toISOString(),
      spikesMetrics: {
        setting: 92, perception: 85, invitation: 78,
        knowledge: 88, emotions: 75, strategy: 82,
      },
      conversationMetrics: { empathyScore: 80, openQuestionRatio: 0.65 },
      dialogueExamples: {
        strong: [{ text: 'I can see this is weighing on you.', context: 'Emotions' }],
        weak: [{ text: 'Don’t worry.', context: 'After diagnosis', improvement: 'Acknowledge feelings first.' }],
      },
    }
  }
}

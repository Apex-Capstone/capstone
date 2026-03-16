// src/api/research.api.ts
// import api from '@/api/client'

export interface ResearchData {
  anonymizedSessions: Array<{
    sessionId: string
    demographics: { ageGroup: string; gender: string }
    scores: { empathy: number; communication: number; clinical: number }
    timestamp: string
  }>
  fairnessMetrics?: {
    biasProbeConsistency: number
    demographicParity: number
    equalizedOdds: number
  }
}

// const BASE = '/v1/research'

export const fetchResearchData = async (): Promise<ResearchData> => {
  // Real call:
  // const { data } = await api.get<ResearchData>(`${BASE}/data`)
  // return data

  // --- dev fallback ---
  await new Promise((r) => setTimeout(r, 300))
  return {
    anonymizedSessions: [
      { sessionId: 'anon_001', demographics: { ageGroup: '25-35', gender: 'female' }, scores: { empathy: 85, communication: 78, clinical: 82 }, timestamp: '2024-01-15T10:00:00Z' },
      { sessionId: 'anon_002', demographics: { ageGroup: '35-45', gender: 'male' }, scores: { empathy: 72, communication: 88, clinical: 79 }, timestamp: '2024-01-14T14:30:00Z' },
      { sessionId: 'anon_003', demographics: { ageGroup: '25-35', gender: 'other' }, scores: { empathy: 91, communication: 85, clinical: 87 }, timestamp: '2024-01-13T09:15:00Z' },
    ],
    fairnessMetrics: {
      biasProbeConsistency: 0.87,
      demographicParity: 0.92,
      equalizedOdds: 0.89,
    },
  }
}

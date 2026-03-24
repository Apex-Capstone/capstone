export interface TraineeSessionAnalyticsDTO {
  session_id: number
  case_id: number
  case_title: string
  empathy_score: number
  communication_score: number
  clinical_score: number
  spikes_completion_score: number
  spikes_coverage_percent: number
  duration_seconds: number
  created_at: string
  eo_addressed_rate?: number | null
}

export interface TraineeSessionAnalytics {
  sessionId: number
  caseId: number
  caseTitle: string
  empathyScore: number
  communicationScore: number
  clinicalScore: number
  spikesCompletionScore: number
  spikesCoveragePercent: number
  durationSeconds: number
  createdAt: string
  eoAddressedRate?: number
}


export interface TraineeSessionAnalyticsDTO {
  session_id: number
  case_id: number
  case_title: string
  empathy_score: number
  communication_score: number
  clinical_score: number
  spikes_completion_score: number
  spikes_coverage_percent: number
  overall_score?: number | null
  duration_seconds: number
  created_at: string
  eo_addressed_rate?: number | null
  spikes_stages_covered?: string[] | null
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
  /** Backend-provided overall score when available; otherwise computed on the client. */
  overallScore?: number
  durationSeconds: number
  createdAt: string
  eoAddressedRate?: number
  /** SPIKES stage codes present in the session (e.g. S, P, I), when available from feedback. */
  spikesStagesCovered?: string[]
}


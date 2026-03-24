import api from '@/api/client'
import type {
  TraineeSessionAnalytics,
  TraineeSessionAnalyticsDTO,
} from '@/types/analytics'

const BASE = '/v1/analytics'

function fromDTO(dto: TraineeSessionAnalyticsDTO): TraineeSessionAnalytics {
  return {
    sessionId: dto.session_id,
    caseId: dto.case_id,
    caseTitle: dto.case_title,
    empathyScore: dto.empathy_score,
    communicationScore: dto.communication_score,
    clinicalScore: dto.clinical_score,
    spikesCompletionScore: dto.spikes_completion_score,
    spikesCoveragePercent: dto.spikes_coverage_percent,
    durationSeconds: dto.duration_seconds,
    createdAt: dto.created_at,
    eoAddressedRate:
      typeof dto.eo_addressed_rate === 'number' ? dto.eo_addressed_rate : undefined,
  }
}

export async function fetchMySessionAnalytics(): Promise<TraineeSessionAnalytics[]> {
  const { data } = await api.get<TraineeSessionAnalyticsDTO[]>(`${BASE}/my-sessions`)
  return data.map(fromDTO)
}


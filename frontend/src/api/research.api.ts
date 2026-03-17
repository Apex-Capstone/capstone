// src/api/research.api.ts
import api from '@/api/client'
import type { AxiosError } from 'axios'

const BASE = '/v1/research'

/** Backend anonymized session shape from GET /v1/research/sessions */
export interface ResearchSessionDTO {
  session_id: string | number
  case_id: number
  duration_seconds: number
  state: string
  spikes_stage?: string | null
  empathy_score?: number | null
  communication_score?: number | null
  clinical_score?: number | null
  timestamp?: string | null
}

export interface ResearchSessionsResponse {
  sessions: ResearchSessionDTO[]
  total: number
  skip: number
  limit: number
}

/** Mapped shape for Research page (backend does not provide demographics/scores) */
export interface ResearchData {
  anonymizedSessions: Array<{
    sessionId: string
    demographics: { ageGroup: string; gender: string }
    scores: { empathy: number | null; communication: number | null; clinical: number | null }
    timestamp: string
    duration_seconds?: number
    state?: string
    spikes_stage?: string | null
  }>
  fairnessMetrics?: {
    biasProbeConsistency: number
    demographicParity: number
    equalizedOdds: number
  }
}

function isForbidden(err: unknown): boolean {
  return (err as AxiosError)?.response?.status === 403
}

/**
 * Fetch anonymized sessions from research API.
 * Requires admin auth; JWT sent via Authorization header.
 * @throws Error with message including "403" or "access denied" when non-admin
 */
export async function fetchResearchSessions(
  skip = 0,
  limit = 100
): Promise<ResearchSessionsResponse> {
  try {
    const { data } = await api.get<ResearchSessionsResponse>(`${BASE}/sessions`, {
      params: { skip, limit },
    })
    return data
  } catch (err) {
    if (isForbidden(err)) {
      throw new Error('Access denied. Admin privileges required.')
    }
    throw err
  }
}

/**
 * Trigger download of anonymized research data as JSON.
 * Requires admin auth.
 * @throws Error with message including "access denied" when 403
 */
export async function fetchResearchExport(): Promise<void> {
  try {
    const { data } = await api.get<Blob>(`${BASE}/export`, {
      responseType: 'blob',
      headers: { Accept: 'application/json' },
    })
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'research_export.json'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (err) {
    if (isForbidden(err)) {
      throw new Error('Access denied. Admin privileges required.')
    }
    throw err
  }
}

/**
 * Fetch research data for the Research dashboard.
 * Maps backend sessions to ResearchData. Backend does not provide demographics
 * or fairness metrics; those fields use placeholders.
 */
export async function fetchResearchData(): Promise<ResearchData> {
  const res = await fetchResearchSessions(0, 500)
  const clampOrNull = (value: number | null | undefined): number | null => {
    if (typeof value !== 'number' || !Number.isFinite(value)) return null
    return Math.max(0, Math.min(100, value))
  }

  const anonymizedSessions = res.sessions.map((s) => {
    const empathy = clampOrNull(s.empathy_score)
    const communication = clampOrNull(s.communication_score)
    const clinical = clampOrNull(s.clinical_score)

    return {
      sessionId: String(s.session_id),
      demographics: { ageGroup: '—', gender: '—' } as const,
      scores: { empathy, communication, clinical } as const,
      timestamp: s.timestamp ?? '',
      duration_seconds: s.duration_seconds,
      state: s.state,
      spikes_stage: s.spikes_stage ?? null,
    }
  })
  return {
    anonymizedSessions,
    // Backend does not provide fairness metrics; omit so UI hides that section
    fairnessMetrics: undefined,
  }
}

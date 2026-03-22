// src/api/admin.api.ts
import api from '@/api/client'
import type { SessionDetailDTO } from '@/types/session'

// Wire types matching backend admin responses (snake_case)
export interface MetricsTimelineDTO {
  turn_number: number
  timestamp: string
  empathy_score: number
  question_type: string
  spikes_stage: string
}

export interface AdminSessionListResponse {
  sessions: SessionDetailDTO[]
  total: number
  skip: number
  limit: number
}

export interface AdminFeedbackSummaryDTO {
  empathy_score: number
  overall_score: number
  strengths?: string | null
  areas_for_improvement?: string | null
}

export interface AdminSessionDetailResponse {
  session: SessionDetailDTO
  feedback: AdminFeedbackSummaryDTO | null
  metrics_timeline: MetricsTimelineDTO[]
}

export interface AdminStats {
  totalUsers: number
  totalCases: number
  activeSessions: number
  averageScore: number
  /** Reserved for a future audit/activity feed; overview uses `fetchAdminSessions` instead. */
  recentActivity: Array<{
    userId: string
    action: string
    timestamp: string
  }>
  /** From `/v1/admin/aggregates` session_stats */
  completedSessions?: number
  totalSessions?: number
  averageDurationSeconds?: number
  /** From user_stats */
  activeUsersLast30Days?: number
  usersByRole?: Record<string, number>
  /** From performance_stats */
  averageEmpathyScore?: number
  averageCommunicationScore?: number
  averageSpikesCompletion?: number
  /** From case_stats */
  casesByCategory?: Record<string, number>
  userOverview?: Array<{
    id: string
    name: string
    email: string
    role: 'trainee' | 'admin'
    averageScore: number
    completedCases: number
    lastActive: string
  }>
  analyticsData?: {
    /** Backend aggregates omit time series; UI shows empty state when []. */
    averageScoreByMonth: Array<{ month: string; score: number }>
    /** Share of sessions per case title (rate = count / total_sessions). Empty if backend sends no per-case counts. */
    completionRates: Array<{ difficulty: string; rate: number }>
    /** Mapped from case_stats.cases_by_category. */
    commonChallenges: Array<{ challenge: string; frequency: number }>
  }
}

interface AggregatesResponse {
  user_stats: {
    total_users: number
    users_by_role: Record<string, number>
    active_users_last_30_days: number
  }
  session_stats: {
    total_sessions: number
    completed_sessions: number
    active_sessions: number
    average_duration_seconds: number
    sessions_by_case: Record<string, number>
  }
  performance_stats: {
    average_empathy_score: number
    average_communication_score: number
    average_spikes_completion: number
    average_overall_score: number
  }
  case_stats: {
    total_cases: number
    cases_by_category: Record<string, number>
  }
  generated_at?: string
}

function completionRatesFromSessionsByCase(
  sessionsByCase: Record<string, number>,
  totalSessions: number
): Array<{ difficulty: string; rate: number }> {
  if (totalSessions <= 0) return []
  return Object.entries(sessionsByCase)
    .map(([caseTitle, count]) => ({
      difficulty: caseTitle,
      rate: count / totalSessions,
    }))
    .sort((a, b) => b.rate - a.rate)
}

function commonChallengesFromCategories(
  casesByCategory: Record<string, number>
): Array<{ challenge: string; frequency: number }> {
  return Object.entries(casesByCategory).map(([challenge, frequency]) => ({
    challenge,
    frequency,
  }))
}

// If your backend path is protected and versioned:
const BASE = '/v1/admin'

export const fetchAdminStats = async (): Promise<AdminStats> => {
  const { data } = await api.get<AggregatesResponse>(`${BASE}/aggregates`)

  const totalSessions = data.session_stats.total_sessions
  const sessionsByCase = data.session_stats.sessions_by_case ?? {}
  const casesByCategory = data.case_stats.cases_by_category ?? {}

  return {
    totalUsers: data.user_stats.total_users,
    totalCases: data.case_stats.total_cases,
    activeSessions: data.session_stats.active_sessions,
    averageScore: data.performance_stats.average_overall_score,
    recentActivity: [],
    completedSessions: data.session_stats.completed_sessions,
    totalSessions: data.session_stats.total_sessions,
    averageDurationSeconds: data.session_stats.average_duration_seconds,
    activeUsersLast30Days: data.user_stats.active_users_last_30_days,
    usersByRole: data.user_stats.users_by_role,
    averageEmpathyScore: data.performance_stats.average_empathy_score,
    averageCommunicationScore: data.performance_stats.average_communication_score,
    averageSpikesCompletion: data.performance_stats.average_spikes_completion,
    casesByCategory,
    analyticsData: {
      averageScoreByMonth: [],
      completionRates: completionRatesFromSessionsByCase(sessionsByCase, totalSessions),
      commonChallenges: commonChallengesFromCategories(casesByCategory),
    },
  }
}

/**
 * Fetch admin session list (user transcripts).
 * Requires admin auth; JWT is sent via Authorization header by api client.
 */
export async function fetchAdminSessions(
  skip = 0,
  limit = 20
): Promise<AdminSessionListResponse> {
  const { data } = await api.get<AdminSessionListResponse>(`${BASE}/sessions`, {
    params: { skip, limit },
  })
  return data
}

/**
 * Fetch admin session detail with transcript and metrics timeline.
 * Requires admin auth; JWT is sent via Authorization header by api client.
 */
export async function fetchAdminSessionDetail(
  sessionId: string
): Promise<AdminSessionDetailResponse> {
  const { data } = await api.get<AdminSessionDetailResponse>(
    `${BASE}/sessions/${sessionId}`
  )
  return data
}

/** Active plugins (module:ClassName) for admin Developer Tools. */
export interface PluginsResponse {
  patient_model: string
  evaluator: string
  metrics: string[]
}

/**
 * Fetch active plugin paths. Admin only.
 */
export async function fetchAdminPlugins(): Promise<PluginsResponse> {
  const { data } = await api.get<PluginsResponse>(`${BASE}/plugins`)
  return data
}

/** Plugin discovery: name + version for dropdowns (e.g. case evaluator). */
export interface PluginInfo {
  name: string
  version: string
}

export interface PluginDiscoveryResponse {
  evaluators: PluginInfo[]
  patient_models: PluginInfo[]
  metrics: PluginInfo[]
}

/**
 * Fetch registered plugins (name + version). Admin only. Use for case evaluator dropdown.
 */
export async function fetchAdminPluginRegistry(): Promise<PluginDiscoveryResponse> {
  const { data } = await api.get<PluginDiscoveryResponse>(`${BASE}/plugin-registry`)
  return data
}

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
  recentActivity: Array<{
    userId: string
    action: string
    timestamp: string
  }>
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
    averageScoreByMonth: Array<{ month: string; score: number }>
    completionRates: Array<{ difficulty: string; rate: number }>
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
}

// If your backend path is protected and versioned:
const BASE = '/v1/admin'

export const fetchAdminStats = async (): Promise<AdminStats> => {
  const { data } = await api.get<AggregatesResponse>(`${BASE}/aggregates`)

  // --- dev fallback (previously used) ---
  // await new Promise((r) => setTimeout(r, 300))
  // return {
  //   totalUsers: 150,
  //   totalCases: 342,
  //   activeSessions: 23,
  //   averageScore: 82.5,
  //   recentActivity: [
  //     { userId: 'trainee_001', action: 'Completed "Delivering a Difficult Diagnosis" case', timestamp: '2024-01-15T15:30:00Z' },
  //     { userId: 'trainee_023', action: 'Started "Responding to Patient Distress" case', timestamp: '2024-01-15T15:25:00Z' },
  //     { userId: 'trainee_045', action: 'Viewed SPIKES feedback for session_789', timestamp: '2024-01-15T15:20:00Z' },
  //   ],
  //   userOverview: [
  //     { id: 'trainee_001', name: 'Dr. Sarah Johnson', email: 'sarah.johnson@medical.edu', role: 'trainee', averageScore: 87.2, completedCases: 12, lastActive: '2024-01-15T15:30:00Z' },
  //     { id: 'trainee_023', name: 'Dr. Michael Chen', email: 'michael.chen@medical.edu', role: 'trainee', averageScore: 79.5, completedCases: 8, lastActive: '2024-01-15T15:25:00Z' },
  //     { id: 'trainee_045', name: 'Dr. Emma Williams', email: 'emma.williams@medical.edu', role: 'trainee', averageScore: 91.3, completedCases: 15, lastActive: '2024-01-15T15:20:00Z' },
  //   ],
  //   analyticsData: {
  //     averageScoreByMonth: [
  //       { month: 'Oct 2024', score: 82.5 },
  //       { month: 'Nov 2024', score: 84.1 },
  //       { month: 'Dec 2024', score: 83.8 },
  //     ],
  //     completionRates: [
  //       { difficulty: 'beginner', rate: 0.95 },
  //       { difficulty: 'intermediate', rate: 0.87 },
  //       { difficulty: 'advanced', rate: 0.72 },
  //     ],
  //     commonChallenges: [
  //       { challenge: 'SPIKES: Emotions stage', frequency: 45 },
  //       { challenge: 'Patient reassurance techniques', frequency: 32 },
  //       { challenge: 'Breaking bad news timing', frequency: 28 },
  //     ],
  //   },
  // }

  return {
    totalUsers: data.user_stats.total_users,
    totalCases: data.case_stats.total_cases,
    activeSessions: data.session_stats.active_sessions,
    averageScore: data.performance_stats.average_overall_score,
    recentActivity: [],
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

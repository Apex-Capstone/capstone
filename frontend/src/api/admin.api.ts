// src/api/admin.api.ts
import api from '@/api/client'

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
  sessionLogs?: Array<{
    id: string
    userId: string
    caseId: string
    startTime: string
    endTime?: string
    score?: number
    transcript?: string
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
  //   sessionLogs: [
  //     { id: 'session_789', userId: 'trainee_001', caseId: '1', startTime: '2024-01-15T14:00:00Z', endTime: '2024-01-15T14:35:00Z', score: 85, transcript: 'Session focused on SPIKES framework...' },
  //     { id: 'session_788', userId: 'trainee_023', caseId: '2', startTime: '2024-01-15T13:30:00Z', endTime: '2024-01-15T14:10:00Z', score: 78, transcript: 'Practice session on managing distress...' },
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

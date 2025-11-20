// src/api/admin.api.ts
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
    role: 'student' | 'admin' | 'instructor'
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

export const fetchAdminStats = async (): Promise<AdminStats> => {
  await new Promise((resolve) => setTimeout(resolve, 150))
  return STATIC_STATS
}

const STATIC_STATS: AdminStats = {
  totalUsers: 132,
  totalCases: 58,
  activeSessions: 9,
  averageScore: 84.2,
  recentActivity: [
    {
      userId: 'trainee_001',
      action: 'Completed "Delivering a Difficult Diagnosis"',
      timestamp: '2025-10-25T14:20:00Z',
    },
    {
      userId: 'trainee_017',
      action: 'Reviewed feedback for session_1024',
      timestamp: '2025-10-25T14:05:00Z',
    },
    {
      userId: 'trainee_022',
      action: 'Started "Responding to Patient Distress"',
      timestamp: '2025-10-25T13:45:00Z',
    },
  ],
  userOverview: [
    {
      id: 'trainee_001',
      name: 'Dr. Sarah Johnson',
      email: 'sarah.johnson@medical.edu',
      role: 'trainee',
      averageScore: 87.2,
      completedCases: 12,
      lastActive: '2025-10-25T14:20:00Z',
    },
    {
      id: 'trainee_017',
      name: 'Dr. Alex Brooks',
      email: 'alex.brooks@medical.edu',
      role: 'trainee',
      averageScore: 82.1,
      completedCases: 9,
      lastActive: '2025-10-25T14:05:00Z',
    },
    {
      id: 'admin_003',
      name: 'Dr. Priya Kapoor',
      email: 'priya.kapoor@medical.edu',
      role: 'admin',
      averageScore: 92.7,
      completedCases: 24,
      lastActive: '2025-10-25T13:50:00Z',
    },
  ],
  sessionLogs: [
    {
      id: 'session_1024',
      userId: 'trainee_001',
      caseId: '7',
      startTime: '2025-10-25T13:10:00Z',
      endTime: '2025-10-25T13:45:00Z',
      score: 90,
      transcript: 'Focused on sharing difficult diagnoses with empathy...',
    },
    {
      id: 'session_1023',
      userId: 'trainee_017',
      caseId: '12',
      startTime: '2025-10-25T12:30:00Z',
      endTime: '2025-10-25T12:55:00Z',
      score: 81,
      transcript: 'Worked on handling patient distress while closing the conversation.',
    },
  ],
  analyticsData: {
    averageScoreByMonth: [
      { month: 'Aug 2025', score: 83.3 },
      { month: 'Sep 2025', score: 85.0 },
      { month: 'Oct 2025', score: 84.2 },
    ],
    completionRates: [
      { difficulty: 'beginner', rate: 0.96 },
      { difficulty: 'intermediate', rate: 0.88 },
      { difficulty: 'advanced', rate: 0.74 },
    ],
    commonChallenges: [
      { challenge: 'Opening difficult conversations', frequency: 32 },
      { challenge: 'SPIKES: Emotion handling', frequency: 27 },
      { challenge: 'Concluding with clarity', frequency: 18 },
    ],
  },
}

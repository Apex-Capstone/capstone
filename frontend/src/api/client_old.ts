import axios from 'axios'

// Base URL from environment variable
// TODO: Replace with actual FastAPI backend URL when backend is ready
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Create axios instance
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
// TODO: Uncomment when FastAPI backend is ready
// attach token from persisted store/localStorage
apiClient.interceptors.request.use((config) => {
  const raw = localStorage.getItem('auth-storage')
  if (raw) {
    try {
      const parsed = JSON.parse(raw)
      // Zustand's persist commonly stores under { state: { token, user } }
      const token =
        parsed?.state?.token       // <- preferred (Zustand persist)
        ?? parsed?.token           // <- fallback if you stored differently
      if (token) {
        config.headers = config.headers ?? {}
        config.headers.Authorization = `Bearer ${token}`
      }
    } catch {
      // ignore parse errors
    }
  }
  return config
})


// Types
export interface LoginResponse {
  token: string
  user: {
    email: string
    role: 'trainee' | 'admin' | 'instructor'
    name?: string
  }
}

export interface Case {
  id: string
  title: string
  status: 'completed' | 'in_progress' | 'pending'
  createdAt: string
  updatedAt: string
  description?: string
  // TODO: FR-2 - Enhanced case data for SPIKES framework
  patientDemographics?: {
    age: number
    gender: 'male' | 'female' | 'other'
    emotion: 'anxious' | 'withdrawn' | 'angry' | 'confused' | 'cooperative'
  }
  spikesStage?: 'setting' | 'perception' | 'invitation' | 'knowledge' | 'emotions' | 'strategy' | 'completed'
  difficulty: 'beginner' | 'intermediate' | 'advanced'
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface CaseDetail extends Case {
  messages: Message[]
  // TODO: FR-3, FR-4, FR-5 - Enhanced chat interface data
  sessionTimer?: {
    startTime: string
    duration: number // in seconds
  }
  currentSpikesStage?: 'setting' | 'perception' | 'invitation' | 'knowledge' | 'emotions' | 'strategy'
}

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
  // TODO: FR-6, FR-12 - Enhanced feedback with SPIKES coverage
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
  // TODO: FR-7, FR-13, FR-14 - Enhanced admin dashboard data
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

// TODO: FR-8, FR-15 - Research API data interface
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

// Mock data generators
const generateMockCases = (): Case[] => {
  return [
    {
      id: '1',
      title: 'Delivering a Difficult Diagnosis',
      status: 'in_progress',
      createdAt: '2024-01-15T10:00:00Z',
      updatedAt: '2024-01-15T14:30:00Z',
      description: 'Practice the SPIKES framework to deliver cancer diagnosis to a 52-year-old patient',
      patientDemographics: {
        age: 52,
        gender: 'female',
        emotion: 'anxious'
      },
      spikesStage: 'perception',
      difficulty: 'intermediate'
    },
    {
      id: '2',
      title: 'Responding to Patient Distress',
      status: 'completed',
      createdAt: '2024-01-14T09:00:00Z',
      updatedAt: '2024-01-14T16:00:00Z',
      description: 'Navigate emotional reactions when discussing treatment options with a 34-year-old patient',
      patientDemographics: {
        age: 34,
        gender: 'male',
        emotion: 'angry'
      },
      spikesStage: 'completed',
      difficulty: 'advanced'
    },
    {
      id: '3',
      title: 'Breaking Bad News to Family',
      status: 'pending',
      createdAt: '2024-01-13T11:00:00Z',
      updatedAt: '2024-01-13T11:00:00Z',
      description: 'Communicate with family members about prognosis for elderly patient',
      patientDemographics: {
        age: 78,
        gender: 'male',
        emotion: 'withdrawn'
      },
      spikesStage: 'setting',
      difficulty: 'beginner'
    },
    {
      id: '4',
      title: 'Pediatric Terminal Diagnosis',
      status: 'pending',
      createdAt: '2024-01-12T08:00:00Z',
      updatedAt: '2024-01-12T08:00:00Z',
      description: 'Sensitive communication with parents about child\'s terminal condition',
      patientDemographics: {
        age: 7,
        gender: 'female',
        emotion: 'confused'
      },
      spikesStage: 'setting',
      difficulty: 'advanced'
    },
    {
      id: '5',
      title: 'Treatment Refusal Discussion',
      status: 'completed',
      createdAt: '2024-01-11T14:00:00Z',
      updatedAt: '2024-01-11T18:00:00Z',
      description: 'Address patient concerns about recommended treatment plan',
      patientDemographics: {
        age: 45,
        gender: 'other',
        emotion: 'cooperative'
      },
      spikesStage: 'completed',
      difficulty: 'intermediate'
    }
  ]
}

const generateMockMessages = (caseId: string): Message[] => {
  // SPIKES-focused dialogue examples
  const spikesDialogue = {
    '1': [
      {
        id: '1',
        role: 'assistant' as const,
        content: 'I have the test results back from your biopsy. Before we discuss them, I want to make sure you understand what we were looking for. What is your understanding of why we did the biopsy?',
        timestamp: '2024-01-15T10:05:00Z',
      },
      {
        id: '2',
        role: 'user' as const,
        content: 'I know you were checking to see if the lump was cancerous. I\'ve been really worried about it.',
        timestamp: '2024-01-15T10:06:00Z',
      },
      {
        id: '3',
        role: 'assistant' as const,
        content: 'I can see that this has been weighing heavily on you. Your concerns are completely understandable. The results show that the tissue is malignant - meaning it is cancer. I know this is difficult news to hear.',
        timestamp: '2024-01-15T10:07:00Z',
      },
    ],
    '2': [
      {
        id: '1',
        role: 'assistant' as const,
        content: 'I understand you\'re upset about the treatment plan we discussed. Can you help me understand what\'s concerning you the most?',
        timestamp: '2024-01-14T09:05:00Z',
      },
      {
        id: '2',
        role: 'user' as const,
        content: 'This is ridiculous! You\'re telling me I need surgery but you can\'t even guarantee it will work. Why should I put myself through that?',
        timestamp: '2024-01-14T09:06:00Z',
      },
      {
        id: '3',
        role: 'assistant' as const,
        content: 'I can hear how frustrated and scared you are. These feelings are completely valid - facing surgery is a big decision. Let\'s talk about your specific concerns and make sure you have all the information you need.',
        timestamp: '2024-01-14T09:07:00Z',
      },
    ],
    default: [
      {
        id: '1',
        role: 'assistant' as const,
        content: 'Thank you for coming in today. I want to make sure we have privacy and won\'t be interrupted. Is it okay if we discuss your recent test results?',
        timestamp: '2024-01-13T11:05:00Z',
      },
      {
        id: '2',
        role: 'user' as const,
        content: 'Yes, I\'ve been waiting to hear about them. What did you find?',
        timestamp: '2024-01-13T11:06:00Z',
      },
    ]
  }
  
  return spikesDialogue[caseId as keyof typeof spikesDialogue] || spikesDialogue.default
}

// API Functions

/**
 * Login user
 * TODO: Replace with actual FastAPI POST /auth/login endpoint
 * Expected FastAPI endpoint: POST /auth/login
 * Expected request body: { email: string, password: string }
 * Expected response: { token: string, user: { email, role, name } }
//  */
export const loginUser = async (email: string, password: string) => {
  // Calls your FastAPI login endpoint and normalizes the response
  const { data } = await apiClient.post('/v1/auth/login', { email, password })
  // Backend typically returns: { access_token, token_type, user: {...} }
  return {
    token: data.access_token,
    user: data.user,
  }
}
// export const loginUser = async (
//   email: string,
//   password: string
// ): Promise<LoginResponse> => {
//   // Simulate API delay
//   await new Promise((resolve) => setTimeout(resolve, 1000))

//   // Mock response - in production, this will be:
//   // return apiClient.post('/auth/login', { email, password }).then(res => res.data)
  
//   if (email === 'admin@example.com' && password === 'admin123') {
//     return {
//       token: 'mock-jwt-token-admin-' + Date.now(),
//       user: {
//         email: 'admin@example.com',
//         role: 'admin',
//         name: 'Admin User',
//       },
//     }
//   }

//   return {
//     token: 'mock-jwt-token-' + Date.now(),
//     user: {
//       email,
//       role: 'trainee',
//       name: email.split('@')[0],
//     },
//   }
// }

/**
 * Fetch all cases for the current user
 * TODO: Replace with actual FastAPI GET /cases endpoint
 * Expected FastAPI endpoint: GET /cases
 * Expected response: Case[]
 */
export const fetchCases = async (): Promise<Case[]> => {
  try {
    const res = await apiClient.get<Case[]>('/cases')
    return res.data
  } catch (err) {
    console.warn('[fetchCases] falling back to mock data:', err)
    return generateMockCases()
  }
}

export const fetchCase = async (id: string): Promise<CaseDetail> => {
  try {
    const res = await apiClient.get<CaseDetail>(`/cases/${id}`)
    return res.data
  } catch (err) {
    console.warn('[fetchCase] falling back to mock detail:', err)
    const cases = generateMockCases()
    const caseData = cases.find((c) => c.id === id) || cases[0]
    return {
      ...caseData,
      messages: generateMockMessages(id),
      sessionTimer: {
        startTime: new Date(Date.now() - 1800000).toISOString(),
        duration: 1800,
      },
      currentSpikesStage:
        (caseData.spikesStage as 'setting' | 'perception' | 'invitation' | 'knowledge' | 'emotions' | 'strategy') ||
        'setting',
    }
  }
}


/**
 * Fetch feedback for a session
 * TODO: Replace with actual FastAPI GET /feedback/:sessionId endpoint
 * Expected FastAPI endpoint: GET /feedback/{session_id}
 * Expected response: Feedback
 */
export const fetchFeedback = async (sessionId: string): Promise<Feedback> => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 500))

  // Mock response - in production, this will be:
  // return apiClient.get(`/feedback/${sessionId}`).then(res => res.data)
  
  return {
    sessionId,
    caseId: '1',
    overallScore: 85,
    strengths: [
      'Excellent use of empathetic language',
      'Clear explanation of diagnosis using layman terms',
      'Gave patient time to process information',
      'Appropriately checked for understanding'
    ],
    areasForImprovement: [
      'Could have explored patient\'s emotions more deeply',
      'Missed opportunity to address family concerns',
      'Could have provided more specific next steps'
    ],
    recommendations: [
      'Practice the "Ask-Tell-Ask" technique for delivering difficult news',
      'Use more open-ended questions to explore patient feelings',
      'Develop a clearer follow-up plan with timelines'
    ],
    metrics: {
      communication: 88,
      clinicalReasoning: 82,
      empathy: 80,
      professionalism: 90,
    },
    createdAt: '2024-01-15T16:00:00Z',
    // TODO: FR-6, FR-12 - Enhanced feedback with SPIKES coverage
    spikesMetrics: {
      setting: 92,
      perception: 85,
      invitation: 78,
      knowledge: 88,
      emotions: 75,
      strategy: 82
    },
    conversationMetrics: {
      empathyScore: 80,
      openQuestionRatio: 0.65
    },
    dialogueExamples: {
      strong: [
        {
          text: "I can see that this has been weighing heavily on you. Your concerns are completely understandable.",
          context: "Acknowledging patient emotions during diagnosis delivery (SPIKES: Emotions)"
        },
        {
          text: "Before we discuss the results, help me understand what you're most worried about.",
          context: "Checking patient's perception before sharing information (SPIKES: Perception)"
        }
      ],
      weak: [
        {
          text: "Don't worry, everything will be fine.",
          context: "During emotional response to diagnosis",
          improvement: "Acknowledge the patient's emotions rather than dismissing them. Try: 'I can see this is really difficult news.'"
        },
        {
          text: "Here's what we need to do next...",
          context: "Immediately after delivering diagnosis",
          improvement: "Give the patient time to process the information before moving to next steps. Ask: 'How are you feeling about what I've shared so far?'"
        }
      ]
    }
  }
}

/**
 * Fetch admin statistics
 * TODO: Replace with actual FastAPI GET /admin/stats endpoint
 * Expected FastAPI endpoint: GET /admin/stats
 * Expected response: AdminStats
 * Note: Should require admin role authentication
 */
export const fetchAdminStats = async (): Promise<AdminStats> => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 500))

  // Mock response - in production, this will be:
  // return apiClient.get('/admin/stats').then(res => res.data)
  
  return {
    totalUsers: 150,
    totalCases: 342,
    activeSessions: 23,
    averageScore: 82.5,
    recentActivity: [
      {
        userId: 'trainee_001',
        action: 'Completed "Delivering a Difficult Diagnosis" case',
        timestamp: '2024-01-15T15:30:00Z',
      },
      {
        userId: 'trainee_023',
        action: 'Started "Responding to Patient Distress" case',
        timestamp: '2024-01-15T15:25:00Z',
      },
      {
        userId: 'trainee_045',
        action: 'Viewed SPIKES feedback for session_789',
        timestamp: '2024-01-15T15:20:00Z',
      },
    ],
    // TODO: FR-7, FR-13, FR-14 - Enhanced admin dashboard data
    userOverview: [
      {
        id: 'trainee_001',
        name: 'Dr. Sarah Johnson',
        email: 'sarah.johnson@medical.edu',
        role: 'trainee',
        averageScore: 87.2,
        completedCases: 12,
        lastActive: '2024-01-15T15:30:00Z'
      },
      {
        id: 'trainee_023',
        name: 'Dr. Michael Chen',
        email: 'michael.chen@medical.edu',
        role: 'trainee',
        averageScore: 79.5,
        completedCases: 8,
        lastActive: '2024-01-15T15:25:00Z'
      },
      {
        id: 'trainee_045',
        name: 'Dr. Emma Williams',
        email: 'emma.williams@medical.edu',
        role: 'trainee',
        averageScore: 91.3,
        completedCases: 15,
        lastActive: '2024-01-15T15:20:00Z'
      }
    ],
    sessionLogs: [
      {
        id: 'session_789',
        userId: 'trainee_001',
        caseId: '1',
        startTime: '2024-01-15T14:00:00Z',
        endTime: '2024-01-15T14:35:00Z',
        score: 85,
        transcript: 'Session focused on SPIKES framework for delivering cancer diagnosis...'
      },
      {
        id: 'session_788',
        userId: 'trainee_023',
        caseId: '2',
        startTime: '2024-01-15T13:30:00Z',
        endTime: '2024-01-15T14:10:00Z',
        score: 78,
        transcript: 'Practice session on managing patient distress and anger...'
      }
    ],
    analyticsData: {
      averageScoreByMonth: [
        { month: 'Oct 2024', score: 82.5 },
        { month: 'Nov 2024', score: 84.1 },
        { month: 'Dec 2024', score: 83.8 }
      ],
      completionRates: [
        { difficulty: 'beginner', rate: 0.95 },
        { difficulty: 'intermediate', rate: 0.87 },
        { difficulty: 'advanced', rate: 0.72 }
      ],
      commonChallenges: [
        { challenge: 'SPIKES: Emotions stage', frequency: 45 },
        { challenge: 'Patient reassurance techniques', frequency: 32 },
        { challenge: 'Breaking bad news timing', frequency: 28 }
      ]
    }
  }
}

/**
 * Fetch research data for analytics
 * TODO: FR-8, FR-15 - Replace with actual FastAPI GET /research/data endpoint
 * Expected FastAPI endpoint: GET /research/data
 * Expected response: ResearchData
 * Note: Read-only analytics endpoint for research use
 */
export const fetchResearchData = async (): Promise<ResearchData> => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 500))

  // Mock response - in production, this will be:
  // return apiClient.get('/research/data').then(res => res.data)
  
  return {
    anonymizedSessions: [
      {
        sessionId: 'anon_001',
        demographics: { ageGroup: '25-35', gender: 'female' },
        scores: { empathy: 85, communication: 78, clinical: 82 },
        timestamp: '2024-01-15T10:00:00Z'
      },
      {
        sessionId: 'anon_002',
        demographics: { ageGroup: '35-45', gender: 'male' },
        scores: { empathy: 72, communication: 88, clinical: 79 },
        timestamp: '2024-01-14T14:30:00Z'
      },
      {
        sessionId: 'anon_003',
        demographics: { ageGroup: '25-35', gender: 'other' },
        scores: { empathy: 91, communication: 85, clinical: 87 },
        timestamp: '2024-01-13T09:15:00Z'
      }
    ],
    fairnessMetrics: {
      biasProbeConsistency: 0.87,
      demographicParity: 0.92,
      equalizedOdds: 0.89
    }
  }
}

export default apiClient


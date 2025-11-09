// Wire types that match backend responses (snake_case)
export interface CaseDTO {
  id: number
  title: string
  description?: string | null
  script: string
  objectives?: string | null
  difficulty_level?: 'beginner' | 'intermediate' | 'advanced' | string
  category?: string | null
  patient_background?: string | null
  expected_spikes_flow?: string | null
  created_at: string
  updated_at: string
}

export interface CaseListDTO {
  cases: CaseDTO[]
  total: number
}

// UI types (camelCase for the app)
export interface Case {
  id: number
  title: string
  description?: string
  script: string
  objectives?: string
  difficultyLevel?: string
  category?: string
  patientBackground?: string
  expectedSpikesFlow?: string
  createdAt: string
  updatedAt: string
}

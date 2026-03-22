/**
 * Case (scenario) types for admin and trainee flows.
 *
 * @remarks
 * {@link CaseDTO} matches backend JSON (`snake_case`). {@link Case} is the camelCase domain type used in the UI.
 */

/** Wire shape for a training case as returned or accepted by the API. */
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
  evaluator_plugin?: string | null
  patient_model_plugin?: string | null
  metrics_plugins?: string[] | null
  created_at: string
  updated_at: string
}

/** Paginated list of cases from the API. */
export interface CaseListDTO {
  cases: CaseDTO[]
  total: number
}

/** Case entity in camelCase for components and forms. */
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
  evaluatorPlugin?: string | null
  patientModelPlugin?: string | null
  metricsPlugins?: string[] | null
  createdAt: string
  updatedAt: string
}

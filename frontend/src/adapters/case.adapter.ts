import type { Case, CaseDTO } from '@/types/case'

// dto -> domain (camelCase)
export const caseFromDTO = (dto: CaseDTO): Case => ({
  id: dto.id,
  title: dto.title,
  description: dto.description ?? undefined,
  script: dto.script,
  objectives: dto.objectives ?? undefined,
  difficultyLevel: dto.difficulty_level ?? undefined,
  category: dto.category ?? undefined,
  patientBackground: dto.patient_background ?? undefined,
  expectedSpikesFlow: dto.expected_spikes_flow ?? undefined,
  createdAt: dto.created_at,
  updatedAt: dto.updated_at,
})

// domain -> create payload (snake_case)
export const toCreatePayload = (c: Partial<Case>) => ({
  title: c.title!,
  script: c.script!,
  description: c.description ?? null,
  objectives: c.objectives ?? null,
  difficulty_level: (c.difficultyLevel !== undefined && { difficulty_level: c.difficultyLevel }),
  category: c.category ?? null,
  patient_background: c.patientBackground ?? null,
  expected_spikes_flow: c.expectedSpikesFlow ?? null,
})

// domain -> update payload (partial)
export const toUpdatePayload = (c: Partial<Case>) => {
  const p: Record<string, unknown> = {}
  if (c.title !== undefined) p.title = c.title
  if (c.script !== undefined) p.script = c.script
  if (c.description !== undefined) p.description = c.description
  if (c.objectives !== undefined) p.objectives = c.objectives
  if (c.difficultyLevel !== undefined) p.difficulty_level = c.difficultyLevel
  if (c.category !== undefined) p.category = c.category
  if (c.patientBackground !== undefined) p.patient_background = c.patientBackground
  if (c.expectedSpikesFlow !== undefined) p.expected_spikes_flow = c.expectedSpikesFlow
  return p
}

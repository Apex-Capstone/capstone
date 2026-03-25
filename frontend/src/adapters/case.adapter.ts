/**
 * Maps case DTOs to domain objects and builds create/update payloads for `/v1/cases`.
 */
import type { Case, CaseDTO } from '@/types/case'

/**
 * Maps a {@link CaseDTO} from the API to a camelCase {@link Case}.
 *
 * @param dto - Wire-format case
 * @returns Domain case for React state
 */
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
  evaluatorPlugin: dto.evaluator_plugin ?? undefined,
  patientModelPlugin: dto.patient_model_plugin ?? undefined,
  metricsPlugins: dto.metrics_plugins ?? undefined,
  createdAt: dto.created_at,
  updatedAt: dto.updated_at,
})

/**
 * Builds a create-case JSON body with required title/script and snake_case plugin fields.
 *
 * @remarks
 * Uses non-null assertions on `title` and `script`; callers must validate before create.
 *
 * @param c - Partial domain case
 * @returns Request body for `POST /v1/cases`
 */
export const toCreatePayload = (c: Partial<Case>) => ({
  title: c.title!,
  script: c.script!,
  description: c.description ?? null,
  objectives: c.objectives ?? null,
  difficulty_level: c.difficultyLevel ?? 'intermediate',
  category: c.category ?? null,
  patient_background: c.patientBackground ?? null,
  expected_spikes_flow: c.expectedSpikesFlow ?? null,
  evaluator_plugin: c.evaluatorPlugin ?? null,
  patient_model_plugin: c.patientModelPlugin ?? null,
  metrics_plugins: c.metricsPlugins ?? null,
})

/**
 * Builds a partial PATCH body including only keys present on the domain object.
 *
 * @param c - Partial domain case with fields to update
 * @returns Record suitable for `PATCH /v1/cases/:id`
 */
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
  if (c.evaluatorPlugin !== undefined) p.evaluator_plugin = c.evaluatorPlugin
  if (c.patientModelPlugin !== undefined) p.patient_model_plugin = c.patientModelPlugin
  if (c.metricsPlugins !== undefined) p.metrics_plugins = c.metricsPlugins
  return p
}

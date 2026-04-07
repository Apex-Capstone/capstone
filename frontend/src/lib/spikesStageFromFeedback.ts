/**
 * Resolve per-turn SPIKES stage from LLM `stage_turn_mapping` vs baseline turn field.
 */
import type { Feedback, SpikesStageKey } from '@/api/feedback.api'

const CANONICAL_STAGES = new Set<SpikesStageKey>([
  'setting',
  'perception',
  'invitation',
  'knowledge',
  'emotion',
  'strategy',
])

function isSpikesStageKey(value: unknown): value is SpikesStageKey {
  return typeof value === 'string' && CANONICAL_STAGES.has(value as SpikesStageKey)
}

function parseTurnNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value) && value >= 1) {
    return value
  }
  return null
}

/**
 * Builds a validated map of turn number → canonical SPIKES stage from evaluator metadata.
 */
export function getLlmStageMapFromFeedback(feedback: Feedback | null | undefined): Map<number, SpikesStageKey> {
  const out = new Map<number, SpikesStageKey>()
  const raw = feedback?.evaluatorMeta?.llm_output?.stage_turn_mapping
  if (!Array.isArray(raw)) {
    return out
  }

  for (const row of raw) {
    if (row == null || typeof row !== 'object') continue
    const tn = parseTurnNumber((row as { turn_number?: unknown }).turn_number)
    const stage = (row as { stage?: unknown }).stage
    if (tn === null || !isSpikesStageKey(stage)) continue
    out.set(tn, stage)
  }

  return out
}

export function resolveSpikesStageForTurn(params: {
  turnNumber: number
  baselineStage?: string | null
  feedback?: Feedback | null
  /** When provided (e.g. from `useMemo`), avoids rebuilding the map per turn. */
  llmStageMap?: Map<number, SpikesStageKey>
}): string {
  const map = params.llmStageMap ?? getLlmStageMapFromFeedback(params.feedback)
  const llm = map.get(params.turnNumber)
  if (llm !== undefined) return llm

  const b = params.baselineStage
  if (b != null && String(b).trim() !== '') {
    return String(b).trim()
  }

  return '—'
}

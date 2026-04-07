/**
 * SPIKES stage display for Feedback UI.
 *
 * Hybrid evaluators: a single source of truth — `evaluator_meta.llm_output.stage_turn_mapping`.
 * Baseline evaluators: per-turn `turn.spikes_stage` (unchanged).
 */
import type { Feedback, SpikesStageKey } from '@/api/feedback.api'

/** Mirrors `scoring_service._HYBRID_EVALUATOR_PLUGIN_KEYS`. */
const HYBRID_EVALUATOR_PLUGIN_KEYS = new Set<string>([
  'plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator',
  'plugins.evaluators.apex_hybrid_v2_evaluator:ApexHybridV2Evaluator',
])

/** Mirrors `scoring_service._HYBRID_EVALUATOR_CLASS_NAMES`. */
const HYBRID_CLASS_NAMES = new Set<string>(['ApexHybridEvaluator', 'ApexHybridV2Evaluator'])

/**
 * Canonical turn index for SPIKES lookup (1-based). Accepts ints or numeric strings from JSON.
 */
export function normalizeTurnNumberForLookup(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value) && value >= 1) {
    return value
  }
  if (typeof value === 'string') {
    const t = value.trim()
    if (/^\d+$/.test(t)) {
      const n = parseInt(t, 10)
      if (n >= 1) return n
    }
  }
  return null
}

/**
 * Normalizes raw SPIKES stage strings from LLM / legacy payloads to canonical keys.
 * (emotion not empathy; strategy not strategy_and_summary / summary.)
 */
export function normalizeSpikesStageToken(raw: unknown): SpikesStageKey | null {
  if (typeof raw !== 'string') return null
  const value = raw.trim().toLowerCase()
  if (!value) return null
  const stageMap: Record<string, SpikesStageKey> = {
    s: 'setting',
    setting: 'setting',
    p: 'perception',
    perception: 'perception',
    i: 'invitation',
    invitation: 'invitation',
    k: 'knowledge',
    knowledge: 'knowledge',
    e: 'emotion',
    emotion: 'emotion',
    emotions: 'emotion',
    empathy: 'emotion',
    s2: 'strategy',
    strategy: 'strategy',
    summary: 'strategy',
    strategy_and_summary: 'strategy',
  }
  return stageMap[value] ?? null
}

/**
 * True when feedback was produced by a hybrid rule+LLM evaluator (session plugin key / class).
 * Mirrors backend `_is_hybrid_evaluator_context`.
 */
export function isHybridEvaluatorFeedback(feedback: Feedback | null | undefined): boolean {
  const meta = feedback?.evaluatorMeta
  if (meta == null || typeof meta !== 'object') return false
  const sessionPlugins = (meta as { session_plugins?: unknown }).session_plugins
  if (sessionPlugins == null || typeof sessionPlugins !== 'object') return false
  const pluginKey = (sessionPlugins as { evaluator_plugin?: unknown }).evaluator_plugin
  if (typeof pluginKey !== 'string') return false
  const normalized = pluginKey.trim()
  if (!normalized) return false
  if (HYBRID_EVALUATOR_PLUGIN_KEYS.has(normalized)) return true
  const cls = normalized.split(':').pop()?.trim() ?? ''
  return HYBRID_CLASS_NAMES.has(cls)
}

/**
 * Use hybrid SPIKES rules (stage_turn_mapping only) in the UI when we know the session is hybrid
 * **or** when LLM output includes a non-empty mapping (some API payloads omit `session_plugins`
 * on `evaluator_meta` even though mapping is present).
 */
export function shouldUseHybridStageTurnMapping(feedback: Feedback | null | undefined): boolean {
  if (isHybridEvaluatorFeedback(feedback)) return true
  const raw = feedback?.evaluatorMeta?.llm_output?.stage_turn_mapping
  return Array.isArray(raw) && raw.length > 0
}

/**
 * Hybrid-only: validated map turn_number → canonical SPIKES stage from `stage_turn_mapping`.
 */
export function getHybridStageTurnMap(feedback: Feedback | null | undefined): Map<number, SpikesStageKey> {
  const out = new Map<number, SpikesStageKey>()
  const raw = feedback?.evaluatorMeta?.llm_output?.stage_turn_mapping
  if (!Array.isArray(raw)) {
    return out
  }

  for (const row of raw) {
    if (row == null || typeof row !== 'object') continue
    const tn = normalizeTurnNumberForLookup((row as { turn_number?: unknown }).turn_number)
    const canon = normalizeSpikesStageToken((row as { stage?: unknown }).stage)
    if (tn === null || canon === null) continue
    out.set(tn, canon)
  }

  return out
}

/**
 * Hybrid-only: distinct canonical stages present in `stage_turn_mapping`.
 */
export function getHybridCoveredStages(feedback: Feedback | null | undefined): Set<SpikesStageKey> {
  const stages = new Set<SpikesStageKey>()
  for (const s of getHybridStageTurnMap(feedback).values()) {
    stages.add(s)
  }
  return stages
}

const SPIKES_TOTAL_STAGES = 6

/**
 * Hybrid-only: coverage percent from mapping size / 6 (0–100).
 */
export function getHybridCoveragePercent(feedback: Feedback | null | undefined): number {
  const n = getHybridCoveredStages(feedback).size
  return Math.round((n / SPIKES_TOTAL_STAGES) * 100)
}

export type SpikesTurnDisplay =
  | { mode: 'hybrid'; showBadge: false }
  | { mode: 'hybrid'; showBadge: true; stage: SpikesStageKey }
  | { mode: 'baseline'; showBadge: true; label: string }

/**
 * Per-turn SPIKES chip for Conversation Analysis: hybrid uses mapping only; baseline uses `turn.spikesStage`.
 */
export function getDisplayedSpikesStageForTurn(params: {
  turnNumber: number
  baselineStage: string | null | undefined
  feedback: Feedback | null | undefined
  isHybrid: boolean
  hybridMap?: Map<number, SpikesStageKey>
}): SpikesTurnDisplay {
  const { turnNumber, baselineStage, feedback, isHybrid } = params
  const map = params.hybridMap ?? getHybridStageTurnMap(feedback)

  if (isHybrid) {
    const tn = normalizeTurnNumberForLookup(turnNumber)
    if (tn === null) {
      return { mode: 'hybrid', showBadge: false }
    }
    const stage = map.get(tn)
    if (stage === undefined) {
      return { mode: 'hybrid', showBadge: false }
    }
    return { mode: 'hybrid', showBadge: true, stage }
  }

  const b = baselineStage
  if (b != null && String(b).trim() !== '') {
    return { mode: 'baseline', showBadge: true, label: String(b).trim() }
  }
  return { mode: 'baseline', showBadge: true, label: '—' }
}

/**
 * @deprecated Use {@link getHybridStageTurnMap}. Alias for compatibility.
 */
export function getLlmStageMapFromFeedback(feedback: Feedback | null | undefined): Map<number, SpikesStageKey> {
  return getHybridStageTurnMap(feedback)
}

/**
 * Maps known plugin class names to short dashboard labels.
 */
const CANONICAL_LABELS: Record<string, string> = {
  DefaultLLMPatientModel: 'Default LLM patient',
  ApexHybridEvaluator: 'Hybrid evaluator',
  ApexHybridV2Evaluator: 'Hybrid v2 evaluator',
  ApexBaselineEvaluator: 'Baseline evaluator',
  ApexMetrics: 'Default metrics',
}

/**
 * Resolves `path:ClassName` or dotted paths to the final identifier (e.g. class name).
 */
function extractIdentifier(pluginName: string): string {
  const t = pluginName.trim()
  if (!t) return ''
  const afterColon = t.includes(':') ? t.split(':').pop()!.trim() : t
  if (!afterColon) return ''
  if (!afterColon.includes('.')) return afterColon
  return afterColon.split('.').pop()!.trim()
}

function stripPluginSuffix(id: string): string {
  return id.replace(/Plugin$/i, '')
}

/**
 * Splits PascalCase / camelCase identifiers into space-separated words.
 */
function pascalToWords(s: string): string {
  const base = stripPluginSuffix(s)
  if (!base) return ''
  const spaced = base
    .replace(/([a-z\d])([A-Z])/g, '$1 $2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
  return spaced.replace(/\s+/g, ' ').trim()
}

/**
 * Produces a readable plugin label from a raw registry string or class name.
 * Avoids showing full `module.path:Class` in UI when a short label can be derived.
 *
 * @param pluginName - Raw value (may include `module:Class` or dotted paths)
 * @returns Display string, or empty string when input has no usable identifier
 */
export function formatPluginName(pluginName: string | null | undefined): string {
  if (pluginName == null) return ''
  const id = extractIdentifier(String(pluginName))
  if (!id) return ''
  if (CANONICAL_LABELS[id]) return CANONICAL_LABELS[id]
  const words = pascalToWords(id)
  return words || id
}

/**
 * Formats session metrics plugin list for tables and detail views (comma-separated readable names).
 */
export function formatMetricsPluginsDisplay(
  value: string | string[] | null | undefined
): string {
  if (value == null) return ''
  if (Array.isArray(value)) {
    if (!value.length) return ''
    return value
      .map((e) => formatPluginName(String(e)))
      .filter(Boolean)
      .join(', ')
  }
  const trimmed = String(value).trim()
  if (!trimmed) return ''
  try {
    const parsed = JSON.parse(trimmed)
    if (Array.isArray(parsed)) {
      if (!parsed.length) return ''
      return parsed
        .map((entry: unknown) => formatPluginName(String(entry)))
        .filter(Boolean)
        .join(', ')
    }
  } catch {
    // fall through
  }
  return formatPluginName(trimmed)
}

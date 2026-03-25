/**
 * Trainee-facing labels and descriptions for analytics metrics (APEX /analytics).
 * Used by summary cards, charts, and insight copy for consistent naming.
 */

export type AnalyticsMetricId =
  | 'empathy'
  | 'communication'
  | 'clinicalReasoning'
  | 'spikes'
  | 'overall'

export type AnalyticsMetricConfig = {
  id: AnalyticsMetricId
  /** Display name (cards, legends, insight text) */
  label: string
  /** Short label for tight UI (e.g. table headers) */
  shortLabel: string
  /** Trainee-facing tooltip / help copy */
  description: string
  /** Tailwind class for the main numeric value on summary cards */
  valueColorClass: string
  /** Stroke color for line/bar series in Recharts */
  chartColor: string
  /** `dataKey` on session / chart data (omit for overall-only) */
  dataKey?: 'empathy' | 'communication' | 'clinical' | 'spikes'
}

export const ANALYTICS_METRICS: Record<AnalyticsMetricId, AnalyticsMetricConfig> = {
  empathy: {
    id: 'empathy',
    label: 'Empathy',
    shortLabel: 'Empathy',
    description: 'How well you recognized and responded to patient emotions.',
    valueColorClass: 'text-blue-500',
    chartColor: '#3b82f6',
    dataKey: 'empathy',
  },
  communication: {
    id: 'communication',
    label: 'Communication',
    shortLabel: 'Communication',
    description: 'Overall clarity, structure, and appropriateness of your responses.',
    valueColorClass: 'text-purple-500',
    chartColor: '#a855f7',
    dataKey: 'communication',
  },
  clinicalReasoning: {
    id: 'clinicalReasoning',
    label: 'Clinical Reasoning',
    shortLabel: 'Clinical reasoning',
    description: 'How well your questions and responses reflected sound clinical thinking.',
    valueColorClass: 'text-green-500',
    chartColor: '#22c55e',
    dataKey: 'clinical',
  },
  spikes: {
    id: 'spikes',
    label: 'SPIKES',
    shortLabel: 'SPIKES',
    description:
      'How completely you covered the SPIKES bad-news communication framework.',
    valueColorClass: 'text-orange-500',
    chartColor: '#f97316',
    dataKey: 'spikes',
  },
  overall: {
    id: 'overall',
    label: 'Overall',
    shortLabel: 'Overall',
    description: 'Combined performance across the main feedback dimensions.',
    valueColorClass: 'text-slate-700',
    chartColor: '#64748b',
  },
}

/** Summary strip + trend chart series (excludes overall). */
export const ANALYTICS_TREND_METRIC_ORDER: AnalyticsMetricId[] = [
  'empathy',
  'communication',
  'clinicalReasoning',
  'spikes',
]

export function metricLabelForInsightKey(
  key: 'empathy' | 'communication' | 'clinical' | 'spikes'
): string {
  const map: Record<typeof key, AnalyticsMetricId> = {
    empathy: 'empathy',
    communication: 'communication',
    clinical: 'clinicalReasoning',
    spikes: 'spikes',
  }
  return ANALYTICS_METRICS[map[key]].label
}

/** Resolve chart `dataKey` (e.g. from Recharts legend payload) to metric config. */
export function getMetricByDataKey(dataKey: string): AnalyticsMetricConfig | undefined {
  return (Object.keys(ANALYTICS_METRICS) as AnalyticsMetricId[])
    .map((id) => ANALYTICS_METRICS[id])
    .find((m) => m.dataKey === dataKey)
}

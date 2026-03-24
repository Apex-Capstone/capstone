import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  BarChart,
  Bar,
} from 'recharts'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AnalyticsSessionsTable } from '@/components/analytics/AnalyticsSessionsTable'
import { fetchMySessionAnalytics } from '@/api/analytics.api'
import type { TraineeSessionAnalytics } from '@/types/analytics'
import { formatPercent } from '@/utils/format'
import {
  ANALYTICS_METRICS,
  ANALYTICS_TREND_METRIC_ORDER,
  getMetricByDataKey,
  metricLabelForInsightKey,
  type AnalyticsMetricId,
} from '@/components/analytics/analyticsMetricConfig'
import { MetricInfoTooltip } from '@/components/analytics/MetricInfoTooltip'
import {
  DEFAULT_ANALYTICS_TIME_RANGE,
  filterAnalyticsSessionsByTimeRange,
  type AnalyticsTimeRange,
} from '@/components/analytics/analyticsTimeFilter'
import { AnalyticsTimeRangeControl } from '@/components/analytics/AnalyticsTimeRangeControl'
import { AnalyticsEmptyState } from '@/components/analytics/AnalyticsEmptyState'
import { AnalyticsLowDataHint } from '@/components/analytics/AnalyticsLowDataHint'

const average = (values: number[]) =>
  values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0

type AnalyticsSummary =
  | { empty: true }
  | {
      empty: false
      empathy: number
      communication: number
      clinical: number
      spikes: number
      overall: number
      total: number
    }

type LegendPayloadItem = {
  value?: string
  color?: string
  dataKey?: string | number
}

function ProgressLineLegend(props: { payload?: LegendPayloadItem[] }) {
  const { payload } = props
  if (!payload?.length) return null
  return (
    <ul className="flex flex-wrap justify-center gap-x-5 gap-y-2 pt-2 text-sm">
      {payload.map((entry) => {
        const key = entry.dataKey != null ? String(entry.dataKey) : ''
        const metric = getMetricByDataKey(key)
        if (!metric) return null
        return (
          <li key={key} className="flex items-center gap-1.5 text-gray-700">
            <span
              className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: entry.color }}
              aria-hidden
            />
            <span>{metric.label}</span>
            <MetricInfoTooltip description={metric.description} />
          </li>
        )
      })}
    </ul>
  )
}

const SUMMARY_METRIC_IDS: AnalyticsMetricId[] = [
  ...ANALYTICS_TREND_METRIC_ORDER,
  'overall',
]

export const Analytics = () => {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<TraineeSessionAnalytics[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [timeRange, setTimeRange] = useState<AnalyticsTimeRange>(DEFAULT_ANALYTICS_TIME_RANGE)

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchMySessionAnalytics()
        setSessions(data)
      } catch (err) {
        console.error('Failed to load analytics:', err)
        setError('Unable to load analytics right now.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const filteredSessions = useMemo(
    () => filterAnalyticsSessionsByTimeRange(sessions, timeRange),
    [sessions, timeRange]
  )

  const summary = useMemo((): AnalyticsSummary => {
    if (filteredSessions.length === 0) {
      return { empty: true }
    }
    const empathy = average(filteredSessions.map((s) => s.empathyScore))
    const communication = average(filteredSessions.map((s) => s.communicationScore))
    const clinical = average(filteredSessions.map((s) => s.clinicalScore))
    const spikes = average(filteredSessions.map((s) => s.spikesCompletionScore))
    const overall = (empathy + communication + clinical + spikes) / 4
    return {
      empty: false,
      empathy,
      communication,
      clinical,
      spikes,
      overall,
      total: filteredSessions.length,
    }
  }, [filteredSessions])

  const summaryMetricDisplay = (id: AnalyticsMetricId): string => {
    if (summary.empty) return '—'
    switch (id) {
      case 'empathy':
        return formatPercent(summary.empathy)
      case 'communication':
        return formatPercent(summary.communication)
      case 'clinicalReasoning':
        return formatPercent(summary.clinical)
      case 'spikes':
        return formatPercent(summary.spikes)
      case 'overall':
        return formatPercent(summary.overall)
    }
  }

  const trendData = useMemo(
    () =>
      filteredSessions.map((s, index) => ({
        label: `S${index + 1}`,
        date: new Date(s.createdAt).toLocaleDateString(),
        empathy: s.empathyScore,
        communication: s.communicationScore,
        clinical: s.clinicalScore,
        spikes: s.spikesCoveragePercent,
      })),
    [filteredSessions]
  )

  const insight = useMemo(() => {
    if (filteredSessions.length === 0) {
      return 'No sessions in this time range. Try a different time filter or complete more sessions.'
    }

    const withEO = filteredSessions.find((s) => typeof s.eoAddressedRate === 'number')
    if (withEO && typeof withEO.eoAddressedRate === 'number') {
      return `You responded to ${formatPercent(withEO.eoAddressedRate)} of empathy opportunities.`
    }

    if (summary.empty) {
      return 'No sessions in this time range to analyze yet.'
    }

    const scores = [
      { key: 'empathy' as const, value: summary.empathy },
      { key: 'communication' as const, value: summary.communication },
      { key: 'clinical' as const, value: summary.clinical },
      { key: 'spikes' as const, value: summary.spikes },
    ]
    scores.sort((a, b) => b.value - a.value)
    return `Your strongest average area right now is ${metricLabelForInsightKey(scores[0].key)}.`
  }, [filteredSessions, summary])

  if (loading) {
    return (
      <div className="h-screen flex flex-col">
        <Navbar />
        <div className="flex flex-1 min-h-0">
          <Sidebar />
          <main className="flex flex-col gap-6 overflow-y-auto pb-10 md:ml-64">
            <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
              <div className="h-8 w-64 bg-gray-200 rounded animate-pulse mb-2" />
              <div className="h-4 w-80 bg-gray-200 rounded animate-pulse" />
            </div>
          </main>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      <Navbar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex flex-col gap-6 overflow-y-auto pb-10 md:ml-64">
          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            <nav className="mb-4 text-sm text-gray-500">
              <span className="cursor-pointer hover:text-gray-700" onClick={() => navigate('/dashboard')}>
                Dashboard
              </span>
              {' / '}
              <span className="text-gray-900">My Analytics</span>
            </nav>

            <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">My Analytics</h1>
                <p className="mt-2 text-gray-600">
                  Track your communication development across completed sessions.
                </p>
              </div>
              {sessions.length > 0 && (
                <AnalyticsTimeRangeControl
                  className="self-end sm:self-auto"
                  value={timeRange}
                  onChange={setTimeRange}
                />
              )}
            </div>

            {error ? (
              <Card>
                <CardContent className="py-8 text-sm text-red-600">{error}</CardContent>
              </Card>
            ) : sessions.length === 0 ? (
              <AnalyticsEmptyState />
            ) : (
              <div className="space-y-8">
                <AnalyticsLowDataHint sessionCount={sessions.length} />
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
                  {SUMMARY_METRIC_IDS.map((id) => {
                    const m = ANALYTICS_METRICS[id]
                    const labelText = id === 'overall' ? m.label : `Average ${m.label}`
                    return (
                      <Card key={id}>
                        <CardContent className="pt-6 text-center">
                          <div className="flex items-start justify-center gap-1">
                            <p className="text-sm text-gray-600">{labelText}</p>
                            <MetricInfoTooltip description={m.description} className="mt-0.5" />
                          </div>
                          <p className={`mt-1 text-2xl font-bold ${m.valueColorClass}`}>
                            {summaryMetricDisplay(id)}
                          </p>
                        </CardContent>
                      </Card>
                    )
                  })}
                  <Card>
                    <CardContent className="pt-6 text-center">
                      <p className="text-sm text-gray-600">Completed Sessions</p>
                      <p className="mt-1 text-2xl font-bold text-gray-700">
                        {summary.empty ? '0' : summary.total}
                      </p>
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle>Progress Over Time</CardTitle>
                    <CardDescription>
                      Empathy, Communication, Clinical Reasoning, and SPIKES coverage by session date.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[320px] w-full">
                      {trendData.length === 0 ? (
                        <div className="flex h-full items-center justify-center px-4 text-center text-sm text-gray-500">
                          No sessions in this time range. Adjust the filter or complete more sessions.
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={trendData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                            <YAxis domain={[0, 100]} />
                            <RechartsTooltip
                              formatter={(value: unknown, name: unknown) => [
                                formatPercent(typeof value === 'number' ? value : Number(value)),
                                name == null ? '' : String(name),
                              ]}
                            />
                            <Legend content={<ProgressLineLegend />} />
                            <Line
                              type="monotone"
                              dataKey="empathy"
                              stroke={ANALYTICS_METRICS.empathy.chartColor}
                              name={ANALYTICS_METRICS.empathy.label}
                            />
                            <Line
                              type="monotone"
                              dataKey="communication"
                              stroke={ANALYTICS_METRICS.communication.chartColor}
                              name={ANALYTICS_METRICS.communication.label}
                            />
                            <Line
                              type="monotone"
                              dataKey="clinical"
                              stroke={ANALYTICS_METRICS.clinicalReasoning.chartColor}
                              name={ANALYTICS_METRICS.clinicalReasoning.label}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <div className="flex flex-wrap items-center gap-2">
                      <CardTitle>SPIKES Coverage Trend</CardTitle>
                      <MetricInfoTooltip description={ANALYTICS_METRICS.spikes.description} />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px] w-full">
                      {trendData.length === 0 ? (
                        <div className="flex h-full items-center justify-center px-4 text-center text-sm text-gray-500">
                          No sessions in this time range. Adjust the filter or complete more sessions.
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={trendData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="label" />
                            <YAxis domain={[0, 100]} />
                            <RechartsTooltip
                              formatter={(value: unknown, name: unknown) => [
                                formatPercent(typeof value === 'number' ? value : Number(value)),
                                name == null ? '' : String(name),
                              ]}
                            />
                            <Bar
                              dataKey="spikes"
                              fill={ANALYTICS_METRICS.spikes.chartColor}
                              name={ANALYTICS_METRICS.spikes.label}
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="pt-6">
                    <AnalyticsSessionsTable key={timeRange} sessions={filteredSessions} />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Insight</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-gray-700">{insight}</p>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

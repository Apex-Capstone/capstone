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
import { formatPercentWhole } from '@/utils/format'
import {
  ANALYTICS_METRICS,
  ANALYTICS_TREND_METRIC_ORDER,
  getMetricByDataKey,
  type AnalyticsMetricId,
} from '@/components/analytics/analyticsMetricConfig'
import { getAnalyticsCoachingInsight } from '@/components/analytics/analyticsCoachingInsight'
import { MetricInfoTooltip } from '@/components/analytics/MetricInfoTooltip'
import { formatDateInUserTimeZone } from '@/lib/dateTime'
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
    const spikes = average(filteredSessions.map((s) => s.spikesCompletionScore))
    const backendOveralls = filteredSessions
      .map((s) => s.overallScore)
      .filter((v): v is number => typeof v === 'number')
    const overall =
      backendOveralls.length === filteredSessions.length
        ? average(backendOveralls)
        : (empathy + communication + spikes) / 3
    return {
      empty: false,
      empathy,
      communication,
      spikes,
      overall,
      total: filteredSessions.length,
    }
  }, [filteredSessions])

  const summaryMetricDisplay = (id: AnalyticsMetricId): string => {
    if (summary.empty) return '—'
    switch (id) {
      case 'empathy':
        return formatPercentWhole(summary.empathy)
      case 'communication':
        return formatPercentWhole(summary.communication)
      case 'spikes':
        return formatPercentWhole(summary.spikes)
      case 'overall':
        return formatPercentWhole(summary.overall)
    }
  }

  const trendData = useMemo(
    () =>
      filteredSessions.map((s, index) => ({
        label: `S${index + 1}`,
        date: formatDateInUserTimeZone(s.createdAt),
        empathy: s.empathyScore,
        communication: s.communicationScore,
        spikes: s.spikesCoveragePercent,
      })),
    [filteredSessions]
  )

  const insight = useMemo(
    () => getAnalyticsCoachingInsight(filteredSessions, summary),
    [filteredSessions, summary]
  )

  if (loading) {
    return (
      <div className="fixed inset-0 overflow-hidden flex flex-col bg-white">
        <Navbar />
        <div className="flex flex-1 min-h-0">
          <Sidebar />
          <main className="flex-1 min-h-0 overflow-y-auto md:ml-64">
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
    <div className="fixed inset-0 overflow-hidden flex flex-col bg-white">
      <Navbar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 min-h-0 overflow-y-auto md:ml-64">
          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            <nav className="mb-4 text-sm text-gray-500">
              <span className="cursor-pointer hover:text-gray-700" onClick={() => navigate('/dashboard')}>
                Dashboard
              </span>
              {' / '}
              <span className="text-gray-900">My Analytics</span>
            </nav>

            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
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
              <div className="space-y-6">
                <AnalyticsLowDataHint sessionCount={sessions.length} />
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                  {SUMMARY_METRIC_IDS.map((id) => {
                    const m = ANALYTICS_METRICS[id]
                    const labelText = id === 'overall' ? m.label : `Average ${m.label}`
                    return (
                      <Card key={id} className="flex flex-col">
                        <CardContent className="flex flex-1 flex-col items-center justify-between px-4 pb-6 pt-6 text-center">
                          <div className="flex min-h-[2.75rem] w-full items-center justify-center gap-1">
                            <span className="text-center text-sm leading-snug text-gray-600">{labelText}</span>
                            <MetricInfoTooltip description={m.description} />
                          </div>
                          <p className={`mt-3 text-2xl font-bold tabular-nums ${m.valueColorClass}`}>
                            {summaryMetricDisplay(id)}
                          </p>
                        </CardContent>
                      </Card>
                    )
                  })}
                  <Card className="flex flex-col">
                    <CardContent className="flex flex-1 flex-col items-center justify-between px-4 pb-6 pt-6 text-center">
                      <p className="flex min-h-[2.75rem] items-center text-sm text-gray-600">Completed Sessions</p>
                      <p className="mt-3 text-2xl font-bold tabular-nums text-gray-700">
                        {summary.empty ? '0' : summary.total}
                      </p>
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader className="space-y-1 pb-2 pt-5">
                    <CardTitle>Progress Over Time</CardTitle>
                    <CardDescription>Scores by session</CardDescription>
                  </CardHeader>
                  <CardContent className="pb-5 pt-0">
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
                                formatPercentWhole(
                                  typeof value === 'number' ? value : Number(value)
                                ),
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
                          </LineChart>
                        </ResponsiveContainer>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="space-y-1 pb-2 pt-5">
                    <div className="flex flex-wrap items-center gap-2">
                      <CardTitle>SPIKES Coverage Trend</CardTitle>
                      <MetricInfoTooltip description={ANALYTICS_METRICS.spikes.description} />
                    </div>
                    <CardDescription>Scores by session</CardDescription>
                  </CardHeader>
                  <CardContent className="pb-5 pt-0">
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
                                formatPercentWhole(
                                  typeof value === 'number' ? value : Number(value)
                                ),
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
                  <CardContent className="px-4 pb-5 pt-5 sm:px-6">
                    <AnalyticsSessionsTable key={timeRange} sessions={filteredSessions} />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2 pt-5">
                    <CardTitle>Coaching insight</CardTitle>
                  </CardHeader>
                  <CardContent className="pb-5 pt-0">
                    <p className="text-sm leading-relaxed text-gray-700">{insight}</p>
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

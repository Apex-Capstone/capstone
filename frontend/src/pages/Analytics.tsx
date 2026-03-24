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

const average = (values: number[]) =>
  values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0

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

  const summary = useMemo(() => {
    const empathy = average(sessions.map((s) => s.empathyScore))
    const communication = average(sessions.map((s) => s.communicationScore))
    const clinical = average(sessions.map((s) => s.clinicalScore))
    const spikes = average(sessions.map((s) => s.spikesCompletionScore))
    const overall =
      sessions.length === 0 ? 0 : (empathy + communication + clinical + spikes) / 4
    return { empathy, communication, clinical, spikes, overall, total: sessions.length }
  }, [sessions])

  const summaryValue = (id: AnalyticsMetricId): number => {
    switch (id) {
      case 'empathy':
        return summary.empathy
      case 'communication':
        return summary.communication
      case 'clinicalReasoning':
        return summary.clinical
      case 'spikes':
        return summary.spikes
      case 'overall':
        return summary.overall
    }
  }

  const trendData = useMemo(
    () =>
      sessions.map((s, index) => ({
        label: `S${index + 1}`,
        date: new Date(s.createdAt).toLocaleDateString(),
        empathy: s.empathyScore,
        communication: s.communicationScore,
        clinical: s.clinicalScore,
        spikes: s.spikesCoveragePercent,
      })),
    [sessions]
  )

  const insight = useMemo(() => {
    const withEO = sessions.find((s) => typeof s.eoAddressedRate === 'number')
    if (withEO && typeof withEO.eoAddressedRate === 'number') {
      return `You responded to ${formatPercent(withEO.eoAddressedRate)} of empathy opportunities.`
    }

    const scores = [
      { key: 'empathy' as const, value: summary.empathy },
      { key: 'communication' as const, value: summary.communication },
      { key: 'clinical' as const, value: summary.clinical },
      { key: 'spikes' as const, value: summary.spikes },
    ]
    scores.sort((a, b) => b.value - a.value)
    return `Your strongest average area right now is ${metricLabelForInsightKey(scores[0].key)}.`
  }, [sessions, summary])

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

            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900">My Analytics</h1>
              <p className="mt-2 text-gray-600">
                Track your communication development across completed sessions.
              </p>
            </div>

            {error ? (
              <Card>
                <CardContent className="py-8 text-sm text-red-600">{error}</CardContent>
              </Card>
            ) : sessions.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center text-gray-600">
                  No completed sessions yet. Complete a case to start tracking your analytics.
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-8">
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
                            {formatPercent(summaryValue(id))}
                          </p>
                        </CardContent>
                      </Card>
                    )
                  })}
                  <Card>
                    <CardContent className="pt-6 text-center">
                      <p className="text-sm text-gray-600">Completed Sessions</p>
                      <p className="mt-1 text-2xl font-bold text-gray-700">{summary.total}</p>
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
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="pt-6">
                    <AnalyticsSessionsTable sessions={sessions} />
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

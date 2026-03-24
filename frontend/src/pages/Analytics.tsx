import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
} from 'recharts'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AnalyticsSessionsTable } from '@/components/analytics/AnalyticsSessionsTable'
import { fetchMySessionAnalytics } from '@/api/analytics.api'
import type { TraineeSessionAnalytics } from '@/types/analytics'
import { formatPercent } from '@/utils/format'

const average = (values: number[]) =>
  values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0

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
    return { empathy, communication, clinical, spikes, total: sessions.length }
  }, [sessions])

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
      { label: 'empathy', value: summary.empathy },
      { label: 'communication', value: summary.communication },
      { label: 'clinical', value: summary.clinical },
      { label: 'SPIKES', value: summary.spikes },
    ]
    scores.sort((a, b) => b.value - a.value)
    return `Your strongest average area right now is ${scores[0].label}.`
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
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                  <Card><CardContent className="pt-6 text-center"><p className="text-sm text-gray-600">Average Empathy</p><p className="text-2xl font-bold text-blue-500">{formatPercent(summary.empathy)}</p></CardContent></Card>
                  <Card><CardContent className="pt-6 text-center"><p className="text-sm text-gray-600">Average Communication</p><p className="text-2xl font-bold text-purple-500">{formatPercent(summary.communication)}</p></CardContent></Card>
                  <Card><CardContent className="pt-6 text-center"><p className="text-sm text-gray-600">Average Clinical</p><p className="text-2xl font-bold text-green-500">{formatPercent(summary.clinical)}</p></CardContent></Card>
                  <Card><CardContent className="pt-6 text-center"><p className="text-sm text-gray-600">Average SPIKES</p><p className="text-2xl font-bold text-orange-500">{formatPercent(summary.spikes)}</p></CardContent></Card>
                  <Card><CardContent className="pt-6 text-center"><p className="text-sm text-gray-600">Completed Sessions</p><p className="text-2xl font-bold text-gray-700">{summary.total}</p></CardContent></Card>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle>Progress Over Time</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[320px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trendData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                          <YAxis domain={[0, 100]} />
                          <Tooltip
                            formatter={(value: unknown, name: unknown) => [
                              formatPercent(typeof value === 'number' ? value : Number(value)),
                              name == null ? '' : String(name),
                            ]}
                          />
                          <Legend />
                          <Line type="monotone" dataKey="empathy" stroke="#3b82f6" name="Empathy" />
                          <Line type="monotone" dataKey="communication" stroke="#a855f7" name="Communication" />
                          <Line type="monotone" dataKey="clinical" stroke="#22c55e" name="Clinical" />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>SPIKES Coverage Trend</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={trendData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="label" />
                          <YAxis domain={[0, 100]} />
                          <Tooltip
                            formatter={(value: unknown, name: unknown) => [
                              formatPercent(typeof value === 'number' ? value : Number(value)),
                              name == null ? '' : String(name),
                            ]}
                          />
                          <Bar dataKey="spikes" fill="#f97316" name="SPIKES" />
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


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
import { fetchMySessionAnalytics } from '@/api/analytics.api'
import type { TraineeSessionAnalytics } from '@/types/analytics'

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
      return `You responded to ${Math.round(withEO.eoAddressedRate)}% of empathy opportunities.`
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
          <main className="flex-1 overflow-y-auto md:ml-64">
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
        <main className="flex-1 overflow-y-auto md:ml-64">
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
                  <Card><CardContent className="pt-6 text-center"><p className="text-sm text-gray-600">Average Empathy</p><p className="text-2xl font-bold text-blue-600">{summary.empathy.toFixed(1)}%</p></CardContent></Card>
                  <Card><CardContent className="pt-6 text-center"><p className="text-sm text-gray-600">Average Communication</p><p className="text-2xl font-bold text-purple-600">{summary.communication.toFixed(1)}%</p></CardContent></Card>
                  <Card><CardContent className="pt-6 text-center"><p className="text-sm text-gray-600">Average Clinical</p><p className="text-2xl font-bold text-green-600">{summary.clinical.toFixed(1)}%</p></CardContent></Card>
                  <Card><CardContent className="pt-6 text-center"><p className="text-sm text-gray-600">Average SPIKES</p><p className="text-2xl font-bold text-orange-600">{summary.spikes.toFixed(1)}%</p></CardContent></Card>
                  <Card><CardContent className="pt-6 text-center"><p className="text-sm text-gray-600">Completed Sessions</p><p className="text-2xl font-bold text-gray-700">{summary.total}</p></CardContent></Card>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle>Progress Over Time</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-80 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trendData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                          <YAxis domain={[0, 100]} />
                          <Tooltip />
                          <Legend />
                          <Line type="monotone" dataKey="empathy" stroke="#2563eb" name="Empathy" />
                          <Line type="monotone" dataKey="communication" stroke="#7c3aed" name="Communication" />
                          <Line type="monotone" dataKey="clinical" stroke="#16a34a" name="Clinical" />
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
                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={trendData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="label" />
                          <YAxis domain={[0, 100]} />
                          <Tooltip />
                          <Bar dataKey="spikes" fill="#f97316" name="SPIKES %" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Session History</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left py-2">Session</th>
                            <th className="text-left py-2">Case</th>
                            <th className="text-left py-2">Empathy %</th>
                            <th className="text-left py-2">Communication %</th>
                            <th className="text-left py-2">Clinical %</th>
                            <th className="text-left py-2">SPIKES %</th>
                            <th className="text-left py-2">Date</th>
                          </tr>
                        </thead>
                        <tbody>
                          {sessions.map((s) => (
                            <tr
                              key={s.sessionId}
                              className="border-b cursor-pointer hover:bg-gray-50"
                              onClick={() => navigate(`/feedback/${s.sessionId}`)}
                            >
                              <td className="py-2 font-medium">#{s.sessionId}</td>
                              <td className="py-2">{s.caseTitle}</td>
                              <td className="py-2">{s.empathyScore.toFixed(1)}</td>
                              <td className="py-2">{s.communicationScore.toFixed(1)}</td>
                              <td className="py-2">{s.clinicalScore.toFixed(1)}</td>
                              <td className="py-2">{s.spikesCoveragePercent.toFixed(1)}</td>
                              <td className="py-2 text-gray-500">{new Date(s.createdAt).toLocaleString()}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
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


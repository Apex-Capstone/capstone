import { useEffect, useState } from 'react'
import { fetchResearchData } from '@/api/client'
import type { ResearchData } from '@/api/client'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertTriangle, Database, Shield, BarChart3 } from 'lucide-react'

export const Research = () => {
  const [data, setData] = useState<ResearchData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadData = async () => {
      try {
        const researchData = await fetchResearchData()
        setData(researchData)
      } catch (error) {
        console.error('Failed to fetch research data:', error)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col">
        <Navbar />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 md:ml-64">
            <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
              <div className="mb-8">
                <div className="h-8 w-64 bg-gray-200 rounded animate-pulse mb-2"></div>
                <div className="h-4 w-96 bg-gray-200 rounded animate-pulse"></div>
              </div>
              
              <div className="grid gap-6 lg:grid-cols-2">
                {[1, 2, 3, 4].map((n) => (
                  <div key={n} className="bg-white border rounded-lg p-6 animate-pulse">
                    <div className="h-5 w-32 bg-gray-200 rounded mb-4"></div>
                    <div className="space-y-2">
                      <div className="h-4 w-full bg-gray-200 rounded"></div>
                      <div className="h-4 w-3/4 bg-gray-200 rounded"></div>
                      <div className="h-4 w-1/2 bg-gray-200 rounded"></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </main>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-500">Research data not available</div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 md:ml-64">
          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            {/* TODO: FR-8, FR-15 - Research API view with read-only analytics */}
            <nav className="mb-4 text-sm text-gray-500">
              Dashboard / <span className="text-gray-900">Research Analytics</span>
            </nav>
            
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900">
                Research Analytics Dashboard
              </h1>
              <p className="mt-2 text-gray-600">
                Read-only analytics endpoint for research use • Anonymized session data and fairness metrics
              </p>
              
              {/* Privacy Notice */}
              <div className="mt-4 flex items-start gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                <Shield className="h-5 w-5 text-emerald-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                  <p className="font-medium text-emerald-900 mb-1">Privacy & Ethics Notice</p>
                  <p className="text-emerald-700">
                    All data displayed has been anonymized and aggregated to protect user privacy. 
                    This endpoint is designed for research purposes and fairness auditing only.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-8">
              {/* Fairness Metrics */}
              {data.fairnessMetrics && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart3 className="h-5 w-5 text-purple-600" />
                      Fairness & Bias Metrics
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-6 md:grid-cols-3">
                      <div className="bg-purple-50 p-4 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-purple-900">Bias Probe Consistency</span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            data.fairnessMetrics.biasProbeConsistency >= 0.8 
                              ? "bg-green-100 text-green-800" 
                              : "bg-red-100 text-red-800"
                          }`}>
                            {data.fairnessMetrics.biasProbeConsistency >= 0.8 ? "Good" : "Needs Attention"}
                          </span>
                        </div>
                        <div className="text-2xl font-bold text-purple-700 mb-1">
                          {(data.fairnessMetrics.biasProbeConsistency * 100).toFixed(1)}%
                        </div>
                        <div className="w-full h-2 bg-purple-200 rounded-full">
                          <div 
                            className="h-full bg-purple-600 rounded-full"
                            style={{ width: `${data.fairnessMetrics.biasProbeConsistency * 100}%` }}
                          />
                        </div>
                        <p className="text-xs text-purple-700 mt-2">
                          Measures consistency in model responses across different demographic groups
                        </p>
                      </div>

                      <div className="bg-green-50 p-4 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-green-900">Demographic Parity</span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            data.fairnessMetrics.demographicParity >= 0.85 
                              ? "bg-green-100 text-green-800" 
                              : "bg-red-100 text-red-800"
                          }`}>
                            {data.fairnessMetrics.demographicParity >= 0.85 ? "Good" : "Needs Attention"}
                          </span>
                        </div>
                        <div className="text-2xl font-bold text-green-700 mb-1">
                          {(data.fairnessMetrics.demographicParity * 100).toFixed(1)}%
                        </div>
                        <div className="w-full h-2 bg-green-200 rounded-full">
                          <div 
                            className="h-full bg-green-600 rounded-full"
                            style={{ width: `${data.fairnessMetrics.demographicParity * 100}%` }}
                          />
                        </div>
                        <p className="text-xs text-green-700 mt-2">
                          Equal positive prediction rates across protected groups
                        </p>
                      </div>

                      <div className="bg-emerald-50 p-4 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-emerald-900">Equalized Odds</span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            data.fairnessMetrics.equalizedOdds >= 0.8 
                              ? "bg-green-100 text-green-800" 
                              : "bg-red-100 text-red-800"
                          }`}>
                            {data.fairnessMetrics.equalizedOdds >= 0.8 ? "Good" : "Needs Attention"}
                          </span>
                        </div>
                        <div className="text-2xl font-bold text-emerald-700 mb-1">
                          {(data.fairnessMetrics.equalizedOdds * 100).toFixed(1)}%
                        </div>
                        <div className="w-full h-2 bg-emerald-200 rounded-full">
                          <div 
                            className="h-full bg-emerald-600 rounded-full"
                            style={{ width: `${data.fairnessMetrics.equalizedOdds * 100}%` }}
                          />
                        </div>
                        <p className="text-xs text-emerald-700 mt-2">
                          Equal true positive and false positive rates across groups
                        </p>
                      </div>
                    </div>

                    <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5" />
                        <div className="text-sm text-yellow-800">
                          <p className="font-medium mb-1">Fairness Monitoring</p>
                          <p>
                            These metrics are automatically calculated across all anonymized sessions. 
                            Values below 80% may indicate potential bias and should be investigated further.
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Anonymized Sessions Table */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="h-5 w-5 text-gray-600" />
                    Anonymized Session Data
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-2">Session ID</th>
                          <th className="text-left py-2">Age Group</th>
                          <th className="text-left py-2">Gender</th>
                          <th className="text-left py-2">Empathy Score</th>
                          <th className="text-left py-2">Communication</th>
                          <th className="text-left py-2">Clinical Score</th>
                          <th className="text-left py-2">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.anonymizedSessions.map((session) => (
                          <tr key={session.sessionId} className="border-b">
                            <td className="py-2 font-mono text-xs">{session.sessionId}</td>
                            <td className="py-2">{session.demographics.ageGroup}</td>
                            <td className="py-2 capitalize">{session.demographics.gender}</td>
                            <td className="py-2">
                              <div className="flex items-center gap-2">
                                <div className="w-12 h-2 bg-gray-200 rounded-full">
                                  <div 
                                    className="h-full bg-emerald-500 rounded-full"
                                    style={{ width: `${session.scores.empathy}%` }}
                                  />
                                </div>
                                <span className="font-medium">{session.scores.empathy}%</span>
                              </div>
                            </td>
                            <td className="py-2">
                              <div className="flex items-center gap-2">
                                <div className="w-12 h-2 bg-gray-200 rounded-full">
                                  <div 
                                    className="h-full bg-green-500 rounded-full"
                                    style={{ width: `${session.scores.communication}%` }}
                                  />
                                </div>
                                <span className="font-medium">{session.scores.communication}%</span>
                              </div>
                            </td>
                            <td className="py-2">
                              <div className="flex items-center gap-2">
                                <div className="w-12 h-2 bg-gray-200 rounded-full">
                                  <div 
                                    className="h-full bg-purple-500 rounded-full"
                                    style={{ width: `${session.scores.clinical}%` }}
                                  />
                                </div>
                                <span className="font-medium">{session.scores.clinical}%</span>
                              </div>
                            </td>
                            <td className="py-2 text-xs text-gray-500">
                              {new Date(session.timestamp).toLocaleDateString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="mt-4 text-xs text-gray-500">
                    <p>
                      <strong>Note:</strong> All session IDs are anonymized hashes. No personally identifiable information is stored or displayed.
                      Age groups are binned (e.g., "25-35") to protect individual privacy.
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* Summary Statistics */}
              <div className="grid gap-6 md:grid-cols-3">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Total Sessions</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{data.anonymizedSessions.length}</div>
                    <p className="text-xs text-gray-500 mt-1">Anonymized training sessions</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Average Empathy Score</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {Math.round(data.anonymizedSessions.reduce((sum, s) => sum + s.scores.empathy, 0) / data.anonymizedSessions.length)}%
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Across all sessions</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Gender Distribution</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-1">
                      {['female', 'male', 'other'].map(gender => {
                        const count = data.anonymizedSessions.filter(s => s.demographics.gender === gender).length
                        const percentage = Math.round((count / data.anonymizedSessions.length) * 100)
                        return (
                          <div key={gender} className="flex items-center justify-between text-sm">
                            <span className="capitalize">{gender}</span>
                            <span className="font-medium">{percentage}%</span>
                          </div>
                        )
                      })}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { fetchResearchData, type ResearchData } from '@/api/research.api'
import { useAuthStore } from '@/store/authStore'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { AlertTriangle, Database, Download, Shield, BarChart3 } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const safePercent = (value: number | null | undefined) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 0
  return Math.max(0, Math.min(100, value))
}

const formatTimestamp = (value: string | null | undefined) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString()
}

export const Research = () => {
  const { user } = useAuthStore()
  const [data, setData] = useState<ResearchData | null>(null)
  const [loading, setLoading] = useState(true)
  const [exportingMetrics, setExportingMetrics] = useState(false)
  const [exportingTranscripts, setExportingTranscripts] = useState(false)
  const [exportingSessionId, setExportingSessionId] = useState<string | null>(null)

  const getToken = (): string | null => {
    try {
      const raw = localStorage.getItem('auth-storage')
      if (!raw) return null
      const parsed = JSON.parse(raw)
      return parsed?.state?.token ?? parsed?.token ?? null
    } catch {
      return null
    }
  }

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    window.URL.revokeObjectURL(url)
  }

  const handleDownloadMetricsCsv = async () => {
    const token = getToken()
    if (!token) return
    setExportingMetrics(true)
    try {
      const response = await fetch(`${API_URL}/v1/research/export/metrics.csv`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!response.ok) throw new Error('Metrics export failed')
      const blob = await response.blob()
      downloadBlob(blob, 'session_metrics.csv')
    } catch (err) {
      console.error('Failed to download metrics CSV:', err)
    } finally {
      setExportingMetrics(false)
    }
  }

  const handleDownloadTranscriptsCsv = async () => {
    const token = getToken()
    if (!token) return
    setExportingTranscripts(true)
    try {
      const response = await fetch(`${API_URL}/v1/research/export/transcripts.csv`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!response.ok) throw new Error('Transcripts export failed')
      const blob = await response.blob()
      downloadBlob(blob, 'all_transcripts.csv')
    } catch (err) {
      console.error('Failed to download transcripts CSV:', err)
    } finally {
      setExportingTranscripts(false)
    }
  }

  const handleExportSessionTranscript = async (anonSessionId: string) => {
    const token = getToken()
    if (!token) return
    setExportingSessionId(anonSessionId)
    try {
      const response = await fetch(
        `${API_URL}/v1/research/export/session/${encodeURIComponent(anonSessionId)}.csv`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (!response.ok) throw new Error('Session export failed')
      const blob = await response.blob()
      const safe = anonSessionId.replace(/[^a-zA-Z0-9_]/g, '_').slice(0, 32)
      downloadBlob(blob, `session_${safe}.csv`)
    } catch (err) {
      console.error('Failed to export session transcript:', err)
    } finally {
      setExportingSessionId(null)
    }
  }

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
              <div className="flex flex-wrap items-center justify-between gap-4">
                <h1 className="text-3xl font-bold text-gray-900">
                  Research Analytics Dashboard
                </h1>
                {user?.role === 'admin' && (
                  <div className="flex flex-wrap items-center gap-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleDownloadMetricsCsv}
                      disabled={exportingMetrics}
                    >
                      <Download className="h-4 w-4 mr-2" />
                      {exportingMetrics ? 'Downloading…' : 'Download Metrics CSV'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleDownloadTranscriptsCsv}
                      disabled={exportingTranscripts}
                    >
                      <Download className="h-4 w-4 mr-2" />
                      {exportingTranscripts ? 'Downloading…' : 'Download All Transcripts CSV'}
                    </Button>
                  </div>
                )}
              </div>
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
                        <div className="w-full h-2 bg-gray-200 rounded-full">
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
                        <div className="w-full h-2 bg-gray-200 rounded-full">
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
                        <div className="w-full h-2 bg-gray-200 rounded-full">
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
                          <th className="text-left py-2">SPIKES Stage</th>
                          <th className="text-left py-2">Clinical Score</th>
                          <th className="text-left py-2">Timestamp</th>
                          {user?.role === 'admin' && (
                            <th className="text-left py-2">Actions</th>
                          )}
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
                                    style={{ width: `${safePercent(session.scores.empathy)}%` }}
                                  />
                                </div>
                                <span className="font-medium">
                                  {(session.scores.empathy ?? 0).toFixed(0)}%
                                </span>
                              </div>
                            </td>
                            <td className="py-2 capitalize">
                              {session.spikes_stage ?? '—'}
                            </td>
                            <td className="py-2">
                              <div className="flex items-center gap-2">
                                <div className="w-12 h-2 bg-gray-200 rounded-full">
                                  <div
                                    className="h-full bg-sky-500 rounded-full"
                                    style={{ width: `${safePercent(session.scores.communication)}%` }}
                                  />
                                </div>
                                <span className="font-medium">
                                  {(session.scores.communication ?? 0).toFixed(0)}%
                                </span>
                              </div>
                            </td>
                            <td className="py-2">
                              <div className="flex items-center gap-2">
                                <div className="w-12 h-2 bg-gray-200 rounded-full">
                                  <div
                                    className="h-full bg-indigo-500 rounded-full"
                                    style={{ width: `${safePercent(session.scores.clinical)}%` }}
                                  />
                                </div>
                                <span className="font-medium">
                                  {(session.scores.clinical ?? 0).toFixed(0)}%
                                </span>
                              </div>
                            </td>
                            <td className="py-2 text-xs text-gray-500">
                              {formatTimestamp(session.timestamp)}
                            </td>
                            {user?.role === 'admin' && (
                              <td className="py-2">
                                <Button
                                  variant="secondary"
                                  size="sm"
                                  onClick={() => handleExportSessionTranscript(session.sessionId)}
                                  disabled={exportingSessionId === session.sessionId}
                                >
                                  {exportingSessionId === session.sessionId ? 'Exporting…' : 'Export Transcript'}
                                </Button>
                              </td>
                            )}
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
                      {(() => {
                        const scored = data.anonymizedSessions.filter(
                          (s) => s.scores.empathy !== null && s.scores.empathy !== undefined
                        )
                        if (scored.length === 0) return '0%'
                        const total = scored.reduce(
                          (sum, s) => sum + (s.scores.empathy ?? 0),
                          0
                        )
                        return `${Math.round(total / scored.length)}%`
                      })()}
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

import { useEffect, useState } from 'react'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Breadcrumb } from '@/components/ui/Breadcrumb'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Database, Download } from 'lucide-react'
import {
  downloadMetricsCSV,
  downloadTranscriptsCSV,
  fetchResearchData,
  type ResearchData,
} from '@/api/research.api'
import { useAuthStore } from '@/store/authStore'
import { ResearchSessionsTable } from '@/components/research/ResearchSessionsTable'
import { Button } from '@/components/ui/button'

export const ResearchSessions = () => {
  const { user } = useAuthStore()
  const [data, setData] = useState<ResearchData | null>(null)
  const [loading, setLoading] = useState(true)
  const [exportingMetrics, setExportingMetrics] = useState(false)
  const [exportingTranscripts, setExportingTranscripts] = useState(false)

  const averageEmpathy = (() => {
    if (!data?.anonymizedSessions.length) return 0
    const values = data.anonymizedSessions
      .map((session) => session.scores.empathy)
      .filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
    if (!values.length) return 0
    return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length)
  })()

  const averageClinical = (() => {
    if (!data?.anonymizedSessions.length) return 0
    const values = data.anonymizedSessions
      .map((session) => session.scores.clinical)
      .filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
    if (!values.length) return 0
    return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length)
  })()

  const handleExportMetricsCsv = async () => {
    setExportingMetrics(true)
    try {
      await downloadMetricsCSV()
    } catch (err) {
      console.error('Failed to download metrics CSV:', err)
    } finally {
      setExportingMetrics(false)
    }
  }

  const handleExportTranscriptsCsv = async () => {
    setExportingTranscripts(true)
    try {
      await downloadTranscriptsCSV()
    } catch (err) {
      console.error('Failed to download transcripts CSV:', err)
    } finally {
      setExportingTranscripts(false)
    }
  }

  useEffect(() => {
    const loadData = async () => {
      try {
        const researchData = await fetchResearchData()
        setData(researchData)
      } catch (error) {
        console.error('Failed to fetch research sessions:', error)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  if (loading) {
    return (
      <div className="h-screen flex flex-col">
        <Navbar />
        <div className="flex flex-1 min-h-0">
          <Sidebar />
          <main className="flex-1 overflow-y-auto md:ml-64">
            <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
              <div className="h-8 w-64 bg-gray-200 rounded animate-pulse mb-2"></div>
              <div className="h-4 w-80 bg-gray-200 rounded animate-pulse"></div>
            </div>
          </main>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-500">Research sessions not available</div>
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
            <Breadcrumb
              items={[
                { label: 'Dashboard', href: '/dashboard' },
                { label: 'Research Analytics', href: '/research' },
                { label: 'Sessions' },
              ]}
            />

            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900">Research Sessions</h1>
              <p className="mt-2 text-gray-600">
                Browse anonymized training sessions and experiment configurations.
              </p>
            </div>

            {user?.role === 'admin' && (
              <div className="mb-6 flex flex-wrap items-center justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportMetricsCsv}
                  disabled={exportingMetrics}
                >
                  <Download className="h-4 w-4 mr-2" />
                  {exportingMetrics ? 'Downloading…' : 'Export Metrics CSV'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportTranscriptsCsv}
                  disabled={exportingTranscripts}
                >
                  <Download className="h-4 w-4 mr-2" />
                  {exportingTranscripts ? 'Downloading…' : 'Export Transcripts CSV'}
                </Button>
              </div>
            )}

            <div className="mb-6 grid gap-4 sm:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Total Sessions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{data.anonymizedSessions.length}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Average Empathy Score</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{averageEmpathy}%</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Average Clinical Score</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{averageClinical}%</div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5 text-gray-600" />
                  Anonymized Session Data
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResearchSessionsTable
                  sessions={data.anonymizedSessions}
                  showActions={user?.role === 'admin'}
                  showExperimentMetadata
                />
                <div className="mt-4 text-xs text-gray-500">
                  <p>
                    <strong>Note:</strong> All session IDs are anonymized hashes. No personally
                    identifiable information is stored or displayed. Age groups are binned (e.g.,
                    &quot;25-35&quot;) to protect individual privacy.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </main>
      </div>
    </div>
  )
}

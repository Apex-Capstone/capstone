import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Breadcrumb } from '@/components/ui/Breadcrumb'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Database } from 'lucide-react'
import { fetchResearchData, type ResearchData } from '@/api/research.api'
import { useAuthStore } from '@/store/authStore'
import { ResearchSessionsTable } from '@/components/research/ResearchSessionsTable'
import { formatPluginName } from '@/lib/formatPluginName'

type AnonSession = ResearchData['anonymizedSessions'][number]

const isCompletedSession = (s: AnonSession) =>
  (s.state ?? '').toLowerCase() === 'completed'

/**
 * Formats duration in seconds as Xm Ys (per spec: floor(sec/60), round(sec % 60)).
 */
const formatDurationXmYs = (totalSeconds: number): string => {
  if (!Number.isFinite(totalSeconds) || totalSeconds < 0) return '—'
  const minutes = Math.floor(totalSeconds / 60)
  const remainingSeconds = Math.round(totalSeconds % 60)
  if (remainingSeconds === 60) {
    return `${minutes + 1}m 0s`
  }
  return `${minutes}m ${remainingSeconds}s`
}

/** Median of a sorted numeric array (even length → mean of two middle values). */
const medianSorted = (sorted: number[]): number | null => {
  const n = sorted.length
  if (n === 0) return null
  const mid = Math.floor(n / 2)
  if (n % 2 === 1) return sorted[mid]!
  return (sorted[mid - 1]! + sorted[mid]!) / 2
}

const SPIKES_BIN_LABELS = ['0–20%', '20–40%', '40–60%', '60–80%', '80–100%'] as const

/** Bin index 0..4 for SPIKES % in [0, 100]. */
const binSpikesPercent = (p: number): number => {
  const x = Math.max(0, Math.min(100, p))
  if (x >= 100) return 4
  return Math.min(4, Math.floor(x / 20))
}

/**
 * Prefer `spikes_completion_score`; fall back to coverage / stage heuristics (aligned with sessions table).
 */
const getSpikesCompletionPercent = (s: AnonSession): number | null => {
  const raw = s.spikes_completion_score
  if (typeof raw === 'number' && Number.isFinite(raw)) {
    let p = raw
    if (p >= 0 && p <= 1) p = p * 100
    return Math.max(0, Math.min(100, p))
  }

  const numericCoverage = s.spikes_coverage_percent ?? s.spikes_coverage
  if (typeof numericCoverage === 'number' && Number.isFinite(numericCoverage)) {
    const normalized = numericCoverage <= 1 ? numericCoverage * 100 : numericCoverage
    return Math.max(0, Math.min(100, normalized))
  }

  const rawStage = (s.spikes_stage ?? '').toString().trim().toLowerCase()
  if (!rawStage) return null
  const stageMap: Record<string, number> = {
    s: 17,
    setting: 17,
    p: 33,
    perception: 33,
    i: 50,
    invitation: 50,
    k: 67,
    knowledge: 67,
    e: 83,
    emotion: 83,
    s2: 100,
    summary: 100,
  }
  return stageMap[rawStage] ?? null
}

const formatPluginSummaryLabel = (raw: string) => {
  const label = formatPluginName(raw.trim())
  return label || '—'
}

/** Truncates long case titles for chart axis labels (ellipsis when over `maxLength`). */
function truncateCaseName(name: string, maxLength = 18): string {
  const t = name.trim()
  if (!t) return '—'
  if (t.length <= maxLength) return t
  return `${t.slice(0, maxLength - 1)}…`
}

type SessionsPerCaseRow = {
  /** Short label for X-axis */
  name: string
  /** Full title for tooltip */
  fullLabel: string
  caseId: number
  sessions: number
}

type TopPluginResult = { display: string; count: number }

const mostCommonPlugin = (
  sessions: AnonSession[],
  pick: (s: AnonSession) => string | null | undefined
): TopPluginResult | null => {
  const counts = new Map<string, number>()
  for (const s of sessions) {
    const raw = pick(s)
    const key = raw?.trim() ? raw.trim() : '__empty__'
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  let bestKey: string | null = null
  let bestCount = 0
  for (const [key, count] of counts) {
    if (
      bestKey == null ||
      count > bestCount ||
      (count === bestCount && key < bestKey)
    ) {
      bestKey = key
      bestCount = count
    }
  }
  if (bestKey == null || bestCount === 0) return null
  if (bestKey === '__empty__') return { display: '—', count: bestCount }
  return { display: formatPluginSummaryLabel(bestKey), count: bestCount }
}

export const ResearchSessions = () => {
  const { user } = useAuthStore()
  const [data, setData] = useState<ResearchData | null>(null)
  const [loading, setLoading] = useState(true)

  const summary = useMemo(() => {
    const sessions = data?.anonymizedSessions ?? []

    const empathyValues = sessions
      .map((session) => session.scores.empathy)
      .filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
    const averageEmpathy =
      empathyValues.length === 0
        ? 0
        : Math.round(empathyValues.reduce((sum, value) => sum + value, 0) / empathyValues.length)

    const clinicalValues = sessions
      .map((session) => session.scores.clinical)
      .filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
    const averageClinical =
      clinicalValues.length === 0
        ? 0
        : Math.round(clinicalValues.reduce((sum, value) => sum + value, 0) / clinicalValues.length)

    const completedSessions = sessions.filter(isCompletedSession)
    const durationValues = completedSessions
      .map((s) => s.duration_seconds)
      .filter((d): d is number => typeof d === 'number' && Number.isFinite(d) && d >= 0)

    let medianDurationLabel = '—'
    if (completedSessions.length > 0 && durationValues.length > 0) {
      const sorted = [...durationValues].sort((a, b) => a - b)
      const med = medianSorted(sorted)
      if (med != null) {
        medianDurationLabel = formatDurationXmYs(med)
      }
    }

    const topPatient = mostCommonPlugin(sessions, (s) => s.patientModelPlugin)
    const topEvaluator = mostCommonPlugin(sessions, (s) => s.evaluatorPlugin)

    const sessionsPerCase: SessionsPerCaseRow[] = (() => {
      const counts = new Map<number, { count: number; label: string }>()
      for (const s of sessions) {
        const id = s.caseId
        if (typeof id !== 'number') continue
        const label = s.caseName?.trim() || `Case ${id}`
        const prev = counts.get(id)
        if (prev) {
          prev.count += 1
        } else {
          counts.set(id, { count: 1, label })
        }
      }
      return [...counts.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([caseId, { count, label }]) => {
          const idSuffix = String(caseId).slice(-4)
          const fullLabel = `${label} (#${idSuffix})`
          const name = `${truncateCaseName(label)} (#${idSuffix})`
          return {
            name,
            fullLabel,
            caseId,
            sessions: count,
          }
        })
    })()

    const spikesCoverageBins = (() => {
      const counts = [0, 0, 0, 0, 0]
      for (const s of sessions) {
        const p = getSpikesCompletionPercent(s)
        if (p == null) continue
        counts[binSpikesPercent(p)] += 1
      }
      return SPIKES_BIN_LABELS.map((label, i) => ({
        range: label,
        count: counts[i] ?? 0,
      }))
    })()

    return {
      averageEmpathy,
      averageClinical,
      medianDurationLabel,
      topPatient,
      topEvaluator,
      sessionsPerCase,
      spikesCoverageBins,
    }
  }, [data])

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

            <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
                  <div className="text-2xl font-bold">{summary.averageEmpathy}%</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Average Clinical Score</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{summary.averageClinical}%</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Median Session Duration</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{summary.medianDurationLabel}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Top Patient Model</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {summary.topPatient
                      ? `${summary.topPatient.display} (${summary.topPatient.count} sessions)`
                      : '—'}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Top Evaluator</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {summary.topEvaluator
                      ? `${summary.topEvaluator.display} (${summary.topEvaluator.count} sessions)`
                      : '—'}
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="mb-6 grid w-full max-w-full gap-6 lg:grid-cols-2">
              <Card className="min-w-0 overflow-hidden">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-900">
                    Sessions per Case
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="h-56 w-full min-w-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={summary.sessionsPerCase}
                        margin={{ top: 8, right: 8, left: 0, bottom: 32 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
                        <XAxis
                          dataKey="name"
                          tick={{ fontSize: 11 }}
                          interval={0}
                          angle={-30}
                          textAnchor="end"
                          height={72}
                        />
                        <YAxis
                          allowDecimals={false}
                          tick={{ fontSize: 11 }}
                          width={36}
                        />
                        <Tooltip
                          content={({ active, payload }) => {
                            if (!active || !payload?.length) return null
                            const row = payload[0]?.payload as SessionsPerCaseRow
                            if (!row) return null
                            return (
                              <div className="max-w-xs rounded-md border border-gray-200 bg-white px-3 py-2 text-sm shadow-md">
                                <div className="font-medium leading-snug text-gray-900">
                                  {row.fullLabel}
                                </div>
                                <div className="mt-1 text-gray-600">Sessions: {row.sessions}</div>
                              </div>
                            )
                          }}
                        />
                        <Bar dataKey="sessions" fill="#6366f1" name="Sessions" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card className="min-w-0 overflow-hidden">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-900">
                    SPIKES Coverage Distribution
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="h-56 w-full min-w-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={summary.spikesCoverageBins}
                        margin={{ top: 8, right: 8, left: 0, bottom: 4 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
                        <XAxis dataKey="range" tick={{ fontSize: 11 }} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={36} />
                        <Tooltip
                          contentStyle={{
                            fontSize: 12,
                            borderRadius: 8,
                            border: '1px solid #e5e7eb',
                          }}
                          formatter={(value) => [
                            typeof value === 'number' ? value : Number(value) || 0,
                            'Sessions',
                          ]}
                        />
                        <Bar dataKey="count" fill="#0d9488" name="Sessions" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
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

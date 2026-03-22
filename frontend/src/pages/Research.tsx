/**
 * Admin research dashboard: anonymized session analytics, score trends, and JSON exports.
 */
import { useEffect, useState, useMemo, useRef } from 'react'
import { createPortal } from 'react-dom'
import { fetchResearchData, type ResearchData } from '@/api/research.api'
import { useAuthStore } from '@/store/authStore'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { AlertTriangle, Database, Download, Shield, BarChart3, TrendingUp } from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/** Trailing window for rolling average of daily means (Score Trends, daily view). */
const DAILY_ROLLING_WINDOW_DAYS = 7

/** Minimum width per bucket for horizontal scroll in hourly view (px). */
const HOURLY_POINT_WIDTH_PX = 44

/**
 * Clamps a nullable numeric score to the inclusive 0–100 range for charts.
 *
 * @param value - Raw score or null/undefined
 * @returns Finite percent 0–100
 */
const safePercent = (value: number | null | undefined) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 0
  return Math.max(0, Math.min(100, value))
}

/**
 * Percent string for chart tooltips: clamped 0–100, max 2 decimal places.
 *
 * @param value - Tooltip payload value
 * @returns Percentage string
 */
const formatScoreTooltipPercent = (value: unknown) => {
  const n = typeof value === 'number' ? value : Number.parseFloat(String(value))
  const clamped = safePercent(Number.isFinite(n) ? n : 0)
  return `${Number.parseFloat(String(clamped)).toFixed(2)}%`
}

/**
 * Formats session timestamps for tables; falls back to em dash when invalid.
 *
 * @param value - ISO string or empty
 * @returns Locale string or `—`
 */
const formatTimestamp = (value: string | null | undefined) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString()
}

/**
 * X-axis tick label for daily trend charts.
 *
 * @param ms - Epoch ms for the bucket
 * @returns Short date label
 */
const formatTrendAxisTick = (ms: number) => {
  const d = new Date(ms)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

/**
 * X-axis tick label for hourly trend charts.
 *
 * @param ms - Epoch ms
 * @returns Date + hour label
 */
const formatTrendAxisTickHourly = (ms: number) => {
  const d = new Date(ms)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
  })
}

/**
 * Tooltip title for day-level trend points (local calendar date only).
 *
 * @param label - Recharts label (epoch ms)
 * @returns Long-form date string
 */
const formatScoreTrendTooltipLabel = (label: unknown) => {
  const ms = typeof label === 'number' ? label : Number(label)
  if (!Number.isFinite(ms)) return ''
  const d = new Date(ms)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

/**
 * Tooltip title for hourly trend points.
 *
 * @param label - Recharts label (epoch ms)
 * @returns Date + time string
 */
const formatScoreTrendHourlyTooltipLabel = (label: unknown) => {
  const ms = typeof label === 'number' ? label : Number(label)
  if (!Number.isFinite(ms)) return ''
  const d = new Date(ms)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

/**
 * Tooltip title for weekly buckets (week-of range).
 *
 * @param label - Week start epoch ms
 * @returns Range string
 */
const formatScoreTrendWeeklyTooltipLabel = (label: unknown) => {
  const ms = typeof label === 'number' ? label : Number(label)
  if (!Number.isFinite(ms)) return ''
  const start = new Date(ms)
  if (Number.isNaN(start.getTime())) return ''
  const end = new Date(start)
  end.setDate(end.getDate() + 6)
  const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }
  return `Week of ${start.toLocaleDateString(undefined, { ...opts, year: 'numeric' })} – ${end.toLocaleDateString(undefined, opts)}`
}

/**
 * Builds a local calendar `YYYY-MM-DD` key for grouping.
 *
 * @param timestamp - ISO timestamp
 * @returns Day key or null
 */
const localDayKeyFromTimestamp = (timestamp: string): string | null => {
  const d = new Date(timestamp)
  if (Number.isNaN(d.getTime())) return null
  const y = d.getFullYear()
  const m = d.getMonth() + 1
  const day = d.getDate()
  return `${y}-${String(m).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

/**
 * Converts a day key to epoch ms at local midnight.
 *
 * @param dayKey - `YYYY-MM-DD`
 * @returns Epoch ms or NaN
 */
const localMidnightMsFromDayKey = (dayKey: string): number => {
  const [ys, ms, ds] = dayKey.split('-').map((x) => Number(x))
  if (![ys, ms, ds].every((n) => Number.isFinite(n))) return NaN
  return new Date(ys, ms - 1, ds).getTime()
}

type DailyMeanRow = {
  dayKey: string
  empathy: number
  communication: number
  clinical: number
}

type TrendSession = {
  timestamp: string
  scores: {
    empathy: number | null
    communication: number | null
    clinical: number | null
  }
}

type TrendPoint = {
  time: number
  empathy: number
  communication: number
  clinical: number
}

/**
 * Hourly bucket key including local hour for intraday aggregation.
 *
 * @param timestamp - ISO timestamp
 * @returns `YYYY-MM-DD-HH` or null
 */
const localHourKeyFromTimestamp = (timestamp: string): string | null => {
  const d = new Date(timestamp)
  if (Number.isNaN(d.getTime())) return null
  const y = d.getFullYear()
  const m = d.getMonth() + 1
  const day = d.getDate()
  const h = d.getHours()
  return `${y}-${String(m).padStart(2, '0')}-${String(day).padStart(2, '0')}-${String(h).padStart(2, '0')}`
}

/**
 * Parses an hourly bucket key to epoch ms at the hour start.
 *
 * @param hourKey - Four-part key from {@link localHourKeyFromTimestamp}
 * @returns Epoch ms or NaN
 */
const localHourStartMsFromHourKey = (hourKey: string): number => {
  const parts = hourKey.split('-')
  if (parts.length !== 4) return NaN
  const ys = Number(parts[0])
  const mo = Number(parts[1])
  const ds = Number(parts[2])
  const hs = Number(parts[3])
  if (![ys, mo, ds, hs].every((n) => Number.isFinite(n))) return NaN
  return new Date(ys, mo - 1, ds, hs, 0, 0, 0).getTime()
}

/**
 * Sunday start-of-week (local) for weekly aggregation buckets.
 *
 * @param timestamp - ISO timestamp
 * @returns Week start epoch ms or null
 */
const startOfWeekSundayLocalMs = (timestamp: string): number | null => {
  const d = new Date(timestamp)
  if (Number.isNaN(d.getTime())) return null
  const day = d.getDay()
  const start = new Date(d.getFullYear(), d.getMonth(), d.getDate() - day)
  start.setHours(0, 0, 0, 0)
  return start.getTime()
}

/**
 * Aggregates sessions into hourly mean score points.
 *
 * @param sessions - Anonymized sessions with scores
 * @returns Sorted trend points
 */
const buildHourlyTrendData = (sessions: TrendSession[]): TrendPoint[] => {
  const buckets = new Map<
    string,
    { empathySum: number; communicationSum: number; clinicalSum: number; count: number }
  >()

  for (const s of sessions) {
    const key = localHourKeyFromTimestamp(s.timestamp)
    if (!key) continue
    const e = safePercent(s.scores.empathy)
    const c = safePercent(s.scores.communication)
    const cl = safePercent(s.scores.clinical)
    const prev = buckets.get(key)
    if (prev) {
      prev.empathySum += e
      prev.communicationSum += c
      prev.clinicalSum += cl
      prev.count += 1
    } else {
      buckets.set(key, {
        empathySum: e,
        communicationSum: c,
        clinicalSum: cl,
        count: 1,
      })
    }
  }

  const hourKeys = [...buckets.keys()].sort()
  return hourKeys
    .map((hourKey) => {
      const b = buckets.get(hourKey)!
      const n = b.count
      const time = localHourStartMsFromHourKey(hourKey)
      return {
        time,
        empathy: b.empathySum / n,
        communication: b.communicationSum / n,
        clinical: b.clinicalSum / n,
      }
    })
    .filter((row) => Number.isFinite(row.time))
}

/**
 * Aggregates sessions into weekly mean score points (week starts Sunday local).
 *
 * @param sessions - Anonymized sessions with scores
 * @returns Sorted weekly trend points
 */
const buildWeeklyTrendData = (sessions: TrendSession[]): TrendPoint[] => {
  const buckets = new Map<
    number,
    { empathySum: number; communicationSum: number; clinicalSum: number; count: number }
  >()

  for (const s of sessions) {
    const weekStart = startOfWeekSundayLocalMs(s.timestamp)
    if (weekStart == null) continue
    const e = safePercent(s.scores.empathy)
    const c = safePercent(s.scores.communication)
    const cl = safePercent(s.scores.clinical)
    const prev = buckets.get(weekStart)
    if (prev) {
      prev.empathySum += e
      prev.communicationSum += c
      prev.clinicalSum += cl
      prev.count += 1
    } else {
      buckets.set(weekStart, {
        empathySum: e,
        communicationSum: c,
        clinicalSum: cl,
        count: 1,
      })
    }
  }

  const weekStarts = [...buckets.keys()].sort((a, b) => a - b)
  return weekStarts.map((t) => {
    const b = buckets.get(t)!
    const n = b.count
    return {
      time: t,
      empathy: b.empathySum / n,
      communication: b.communicationSum / n,
      clinical: b.clinicalSum / n,
    }
  })
}

/**
 * Builds per-day rolling averages over `rollingWindowDays` for smoother trend lines.
 *
 * @param sessions - Anonymized sessions with scores
 * @param rollingWindowDays - Trailing window size in days
 * @returns Daily points with rolling means
 */
const buildDailyRollingTrendData = (
  sessions: TrendSession[],
  rollingWindowDays: number
): TrendPoint[] => {
  const buckets = new Map<
    string,
    { empathySum: number; communicationSum: number; clinicalSum: number; count: number }
  >()

  for (const s of sessions) {
    const key = localDayKeyFromTimestamp(s.timestamp)
    if (!key) continue
    const e = safePercent(s.scores.empathy)
    const c = safePercent(s.scores.communication)
    const cl = safePercent(s.scores.clinical)
    const prev = buckets.get(key)
    if (prev) {
      prev.empathySum += e
      prev.communicationSum += c
      prev.clinicalSum += cl
      prev.count += 1
    } else {
      buckets.set(key, {
        empathySum: e,
        communicationSum: c,
        clinicalSum: cl,
        count: 1,
      })
    }
  }

  const dayKeys = [...buckets.keys()].sort()
  const daily: DailyMeanRow[] = dayKeys.map((dayKey) => {
    const b = buckets.get(dayKey)!
    const n = b.count
    return {
      dayKey,
      empathy: b.empathySum / n,
      communication: b.communicationSum / n,
      clinical: b.clinicalSum / n,
    }
  })

  return daily.map((row, i) => {
    const start = Math.max(0, i - rollingWindowDays + 1)
    const windowRows = daily.slice(start, i + 1)
    const w = windowRows.length
    const empathy = windowRows.reduce((sum, r) => sum + r.empathy, 0) / w
    const communication = windowRows.reduce((sum, r) => sum + r.communication, 0) / w
    const clinical = windowRows.reduce((sum, r) => sum + r.clinical, 0) / w
    const time = localMidnightMsFromDayKey(row.dayKey)
    return { time, empathy, communication, clinical }
  }).filter((row) => Number.isFinite(row.time))
}

type ScoreTrendTooltipBodyProps = {
  active?: boolean
  payload?: readonly { name?: string | number; value?: unknown; color?: string }[]
  label?: string | number
  coordinate?: { x: number; y: number }
  chartRef: React.RefObject<HTMLDivElement | null>
  usePortal: boolean
  labelFormatter: (label: unknown) => string
}

/**
 * Custom Recharts tooltip body; optionally portaled for horizontally scrolled charts.
 *
 * @remarks
 * Hourly view uses a wide, scrollable chart: default tooltips are clipped, so `usePortal`
 * renders fixed-position content in `document.body`.
 *
 * @param props - Recharts tooltip props plus chart ref and portal mode
 * @param props.active - Whether the tooltip is visible
 * @param props.payload - Series rows for the hovered point
 * @param props.label - Axis value (epoch ms)
 * @param props.coordinate - Pointer position inside the chart SVG
 * @param props.chartRef - Container used to convert coordinates when portaling
 * @param props.usePortal - When true, render via `createPortal` to `document.body`
 * @param props.labelFormatter - Formats the tooltip title from `label`
 * @returns Tooltip content or null
 */
function ScoreTrendTooltipBody({
  active,
  payload,
  label,
  coordinate,
  chartRef,
  usePortal,
  labelFormatter,
}: ScoreTrendTooltipBodyProps) {
  if (!active || !payload?.length) return null

  const title = labelFormatter(label)

  const inner = (
    <div className="rounded-md border border-gray-200 bg-white px-3 py-2 text-sm shadow-lg max-w-[min(100vw-2rem,16rem)]">
      <div className="font-medium text-gray-900 mb-1 border-b border-gray-100 pb-1">{title}</div>
      <div className="space-y-0.5">
        {payload.map((entry, i) => {
          const raw = entry.value
          const num = Array.isArray(raw) ? Number(raw[0]) : Number(raw)
          return (
            <div key={i} className="flex justify-between gap-4" style={{ color: entry.color }}>
              <span>{entry.name != null ? String(entry.name) : ''}</span>
              <span>{formatScoreTooltipPercent(num)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )

  if (usePortal && coordinate != null && chartRef.current) {
    const rect = chartRef.current.getBoundingClientRect()
    const x = rect.left + coordinate.x
    const y = rect.top + coordinate.y
    const margin = 8
    const approxHalfWidth = 110
    const clampedLeft = Math.min(
      Math.max(x, approxHalfWidth + margin),
      window.innerWidth - approxHalfWidth - margin
    )

    return createPortal(
      <div
        className="pointer-events-none fixed z-[9999]"
        style={{
          left: clampedLeft,
          top: y,
          transform: 'translate(-50%, calc(-100% - 10px))',
        }}
      >
        {inner}
      </div>,
      document.body
    )
  }

  return <div className="pointer-events-none">{inner}</div>
}

type ScoreTrendGranularity = 'hourly' | 'daily' | 'weekly'

/**
 * Admin research page: dataset summary, fairness placeholders, exports, and score trend charts.
 *
 * @returns Research dashboard layout
 */
export const Research = () => {
  const { user } = useAuthStore()
  const [data, setData] = useState<ResearchData | null>(null)
  const [scoreTrendGranularity, setScoreTrendGranularity] =
    useState<ScoreTrendGranularity>('daily')
  const scoreTrendChartRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(true)
  const [exportingMetrics, setExportingMetrics] = useState(false)
  const [exportingTranscripts, setExportingTranscripts] = useState(false)
  const [exportingSessionId, setExportingSessionId] = useState<string | null>(null)

  /**
   * Reads JWT from persisted `auth-storage` for authenticated downloads.
   *
   * @returns Bearer token or null
   */
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

  /**
   * Triggers a browser download for an in-memory blob.
   *
   * @param blob - File contents
   * @param filename - Suggested download name
   */
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

  const trendChartData = useMemo((): TrendPoint[] => {
    if (!data?.anonymizedSessions?.length) return []
    const sessions = data.anonymizedSessions
    switch (scoreTrendGranularity) {
      case 'hourly':
        return buildHourlyTrendData(sessions)
      case 'weekly':
        return buildWeeklyTrendData(sessions)
      case 'daily':
      default:
        return buildDailyRollingTrendData(sessions, DAILY_ROLLING_WINDOW_DAYS)
    }
  }, [data?.anonymizedSessions, scoreTrendGranularity])

  const scoreTrendChartWidthPx = useMemo(() => {
    if (scoreTrendGranularity !== 'hourly') return undefined
    const n = trendChartData.length
    return Math.max(640, n * HOURLY_POINT_WIDTH_PX)
  }, [scoreTrendGranularity, trendChartData.length])

  const scoreTrendTooltipLabelFormatter = useMemo(() => {
    switch (scoreTrendGranularity) {
      case 'hourly':
        return formatScoreTrendHourlyTooltipLabel
      case 'weekly':
        return formatScoreTrendWeeklyTooltipLabel
      case 'daily':
      default:
        return formatScoreTrendTooltipLabel
    }
  }, [scoreTrendGranularity])

  const scoreTrendAxisTickFormatter = useMemo(() => {
    switch (scoreTrendGranularity) {
      case 'hourly':
        return formatTrendAxisTickHourly
      case 'weekly':
      case 'daily':
      default:
        return formatTrendAxisTick
    }
  }, [scoreTrendGranularity])

  const averageScoresChartData = useMemo(() => {
    if (!data?.anonymizedSessions?.length) return []
    const empathyValues = data.anonymizedSessions
      .map((s) => s.scores.empathy)
      .filter((v): v is number => typeof v === 'number' && Number.isFinite(v))
    const communicationValues = data.anonymizedSessions
      .map((s) => s.scores.communication)
      .filter((v): v is number => typeof v === 'number' && Number.isFinite(v))
    const clinicalValues = data.anonymizedSessions
      .map((s) => s.scores.clinical)
      .filter((v): v is number => typeof v === 'number' && Number.isFinite(v))

    const empathyAvg =
      empathyValues.length > 0
        ? Math.round(
            empathyValues.reduce((sum, v) => sum + v, 0) / empathyValues.length
          )
        : 0
    const communicationAvg =
      communicationValues.length > 0
        ? Math.round(
            communicationValues.reduce((sum, v) => sum + v, 0) /
              communicationValues.length
          )
        : 0
    const clinicalAvg =
      clinicalValues.length > 0
        ? Math.round(
            clinicalValues.reduce((sum, v) => sum + v, 0) / clinicalValues.length
          )
        : 0

    return [
      {
        name: 'Empathy',
        value: empathyAvg,
      },
      {
        name: 'Communication',
        value: communicationAvg,
      },
      {
        name: 'Clinical',
        value: clinicalAvg,
      },
    ]
  }, [data?.anonymizedSessions])

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
      <div className="h-screen flex flex-col">
        <Navbar />
        <div className="flex flex-1 min-h-0">
          <Sidebar />
          <main className="flex-1 overflow-y-auto md:ml-64">
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
    <div className="h-screen flex flex-col">
      <Navbar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 overflow-y-auto md:ml-64">
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
              {/* Score trend over time */}
              <Card>
                <CardHeader>
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                      <CardTitle className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-blue-600 shrink-0" />
                        Score Trends
                      </CardTitle>
                      <p className="text-sm text-gray-500 font-normal mt-1">
                        {scoreTrendGranularity === 'hourly' &&
                          'Mean scores per clock hour (local time). Scroll horizontally when there are many hours.'}
                        {scoreTrendGranularity === 'daily' &&
                          `${DAILY_ROLLING_WINDOW_DAYS}-day rolling average of daily mean scores (empathy, communication, clinical). One point per calendar day with sessions.`}
                        {scoreTrendGranularity === 'weekly' &&
                          'Mean scores per calendar week (weeks start Sunday, local time). One point per week with sessions.'}
                      </p>
                    </div>
                    <div
                      className="flex flex-wrap gap-2 shrink-0"
                      role="group"
                      aria-label="Score trend time grouping"
                    >
                      <Button
                        type="button"
                        size="sm"
                        variant={scoreTrendGranularity === 'hourly' ? 'default' : 'outline'}
                        onClick={() => setScoreTrendGranularity('hourly')}
                      >
                        Hourly
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant={scoreTrendGranularity === 'daily' ? 'default' : 'outline'}
                        onClick={() => setScoreTrendGranularity('daily')}
                      >
                        Daily
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant={scoreTrendGranularity === 'weekly' ? 'default' : 'outline'}
                        onClick={() => setScoreTrendGranularity('weekly')}
                      >
                        Weekly
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div
                    className={cn(
                      'w-full',
                      scoreTrendGranularity === 'hourly' &&
                        'overflow-x-auto pb-1 overscroll-x-contain [overflow-anchor:none]'
                    )}
                  >
                    <div
                      ref={scoreTrendChartRef}
                      className="h-72 w-full"
                      style={
                        scoreTrendChartWidthPx != null
                          ? { width: scoreTrendChartWidthPx, minWidth: '100%' }
                          : undefined
                      }
                    >
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trendChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
                          <XAxis
                            dataKey="time"
                            type="number"
                            scale="time"
                            domain={['dataMin', 'dataMax']}
                            tickFormatter={scoreTrendAxisTickFormatter}
                            minTickGap={scoreTrendGranularity === 'hourly' ? 8 : 12}
                            tick={{ fontSize: 12 }}
                          />
                          <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                          <Tooltip
                            content={(props) => (
                              <ScoreTrendTooltipBody
                                active={props.active}
                                payload={
                                  props.payload as ScoreTrendTooltipBodyProps['payload']
                                }
                                label={props.label}
                                coordinate={props.coordinate}
                                chartRef={scoreTrendChartRef}
                                usePortal={scoreTrendGranularity === 'hourly'}
                                labelFormatter={scoreTrendTooltipLabelFormatter}
                              />
                            )}
                            wrapperStyle={
                              scoreTrendGranularity === 'hourly'
                                ? {
                                    opacity: 0,
                                    width: 0,
                                    height: 0,
                                    overflow: 'hidden',
                                    pointerEvents: 'none',
                                  }
                                : undefined
                            }
                            isAnimationActive={false}
                            allowEscapeViewBox={{ x: true, y: true }}
                          />
                          <Legend />
                          <Line type="monotone" dataKey="empathy" stroke="#10b981" strokeWidth={2} name="Empathy %" />
                          <Line type="monotone" dataKey="communication" stroke="#22c55e" strokeWidth={2} name="Communication %" />
                          <Line type="monotone" dataKey="clinical" stroke="#7c3aed" strokeWidth={2} name="Clinical %" />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </CardContent>
              </Card>

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
                    <CardTitle className="text-sm">Average Score Distribution</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-40 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={averageScoresChartData} margin={{ top: 5, right: 5, left: 5, bottom: 20 }}>
                          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-100" />
                          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                          <Tooltip
                            formatter={(value: unknown) =>
                              [formatScoreTooltipPercent(value), 'Average'] as [React.ReactNode, string]
                            }
                          />
                          <Bar dataKey="value" fill="#7c3aed" name="Average %" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Empathy, communication, clinical</p>
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

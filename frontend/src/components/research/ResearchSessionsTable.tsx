import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import type { ResearchData } from '@/api/research.api'
import { formatPluginName as formatPluginNameFromLib } from '@/lib/formatPluginName'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type Session = ResearchData['anonymizedSessions'][number]

type ResearchSessionsTableProps = {
  sessions: Session[]
  showActions?: boolean
  showExperimentMetadata?: boolean
}

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

const formatDuration = (value: number | undefined) => {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return '—'
  const wholeSeconds = Math.floor(value)
  const hours = Math.floor(wholeSeconds / 3600)
  const minutes = Math.floor((wholeSeconds % 3600) / 60)
  const seconds = wholeSeconds % 60
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m ${seconds}s`
}

const formatPluginName = (plugin?: string | null) => {
  if (plugin == null || !String(plugin).trim()) return '—'
  const label = formatPluginNameFromLib(String(plugin).trim())
  return label || '—'
}

type SortKey = 'case' | 'empathy' | 'communication' | 'clinical' | 'spikes' | 'duration' | 'date'

export function ResearchSessionsTable({
  sessions = [],
  showActions = false,
  showExperimentMetadata = false,
}: ResearchSessionsTableProps) {
  const [exportingSessionId, setExportingSessionId] = useState<string | null>(null)
  const [searchText, setSearchText] = useState('')
  const [caseFilter, setCaseFilter] = useState('all')
  const [spikesFilter, setSpikesFilter] = useState('all')
  const [empathyFilter, setEmpathyFilter] = useState('all')
  const [dateFilter, setDateFilter] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [sortBy, setSortBy] = useState<SortKey>('date')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const pageSize = 10
  const safeSessions = Array.isArray(sessions) ? sessions : []

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

  const getSpikesPercent = (session: Session): number | null => {
    const numericCoverage = session?.spikes_coverage_percent ?? session?.spikes_coverage
    if (typeof numericCoverage === 'number' && Number.isFinite(numericCoverage)) {
      const normalized = numericCoverage <= 1 ? numericCoverage * 100 : numericCoverage
      return Math.max(0, Math.min(100, normalized))
    }

    const rawStage = (session?.spikes_stage ?? '').toString().trim().toLowerCase()
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
      empathy: 83,
      s2: 100,
      summary: 100,
    }
    return stageMap[rawStage] ?? null
  }

  const spikesOptions = ['0-25', '25-50', '50-75', '75-100']
  const caseOptions = useMemo(() => {
    const values = new Set<number>()
    for (const session of safeSessions) {
      if (typeof session.caseId === 'number') values.add(session.caseId)
    }
    return [...values].sort((a, b) => a - b)
  }, [safeSessions])

  const filteredSessions = useMemo(() => {
    const nowMs = Date.now()
    return safeSessions.filter((session) => {
      if (
        searchText.trim() &&
        !(session.sessionId ?? '').toLowerCase().includes(searchText.trim().toLowerCase())
      ) {
        return false
      }

      if (caseFilter !== 'all' && String(session.caseId ?? '') !== caseFilter) {
        return false
      }

      const empathy = session.scores?.empathy
      if (empathyFilter !== 'all') {
        if (typeof empathy !== 'number' || !Number.isFinite(empathy)) return false
        if (empathyFilter === '0-25' && !(empathy >= 0 && empathy < 25)) return false
        if (empathyFilter === '25-50' && !(empathy >= 25 && empathy < 50)) return false
        if (empathyFilter === '50-75' && !(empathy >= 50 && empathy < 75)) return false
        if (empathyFilter === '75-100' && !(empathy >= 75 && empathy <= 100)) return false
      }

      if (dateFilter !== 'all') {
        const timestampMs = new Date(session.timestamp).getTime()
        if (Number.isNaN(timestampMs)) return false
        const dayMs = 24 * 60 * 60 * 1000
        if (dateFilter === '24h' && nowMs - timestampMs > dayMs) return false
        if (dateFilter === '7d' && nowMs - timestampMs > 7 * dayMs) return false
        if (dateFilter === '30d' && nowMs - timestampMs > 30 * dayMs) return false
      }

      const spikesPercent = getSpikesPercent(session)
      if (spikesFilter !== 'all') {
        if (spikesPercent == null) return false
        if (spikesFilter === '0-25' && !(spikesPercent >= 0 && spikesPercent < 25)) return false
        if (spikesFilter === '25-50' && !(spikesPercent >= 25 && spikesPercent < 50)) return false
        if (spikesFilter === '50-75' && !(spikesPercent >= 50 && spikesPercent < 75)) return false
        if (spikesFilter === '75-100' && !(spikesPercent >= 75 && spikesPercent <= 100)) return false
      }

      return true
    })
  }, [caseFilter, dateFilter, empathyFilter, searchText, safeSessions, spikesFilter])

  const formatMetricsPlugins = (value: string | null | undefined) => {
    if (!value) return '—'
    const trimmed = value.trim()
    if (!trimmed) return '—'

    try {
      const parsed = JSON.parse(trimmed)
      if (Array.isArray(parsed)) {
        if (!parsed.length) return '—'
        return parsed
          .map((entry) => String(entry))
          .map((entry) => formatPluginName(entry))
          .join(', ')
      }
    } catch {
      // Keep raw fallback below for non-JSON values.
    }

    return formatPluginName(trimmed)
  }

  useEffect(() => {
    setCurrentPage(1)
  }, [searchText, caseFilter, spikesFilter, empathyFilter, dateFilter, sortBy, sortDirection])

  const sortedSessions = useMemo(() => {
    const sorted = [...filteredSessions]
    const direction = sortDirection === 'asc' ? 1 : -1
    sorted.sort((a, b) => {
      let left: number | string = 0
      let right: number | string = 0
      switch (sortBy) {
        case 'case':
          left = a.caseId ?? -1
          right = b.caseId ?? -1
          break
        case 'empathy':
          left = a.scores.empathy ?? -1
          right = b.scores.empathy ?? -1
          break
        case 'communication':
          left = a.scores.communication ?? -1
          right = b.scores.communication ?? -1
          break
        case 'clinical':
          left = a.scores.clinical ?? -1
          right = b.scores.clinical ?? -1
          break
        case 'spikes':
          left = getSpikesPercent(a) ?? -1
          right = getSpikesPercent(b) ?? -1
          break
        case 'duration':
          left = a.duration_seconds ?? -1
          right = b.duration_seconds ?? -1
          break
        case 'date':
        default:
          left = Number.isNaN(new Date(a.timestamp).getTime()) ? 0 : new Date(a.timestamp).getTime()
          right = Number.isNaN(new Date(b.timestamp).getTime()) ? 0 : new Date(b.timestamp).getTime()
          break
      }
      if (left < right) return -1 * direction
      if (left > right) return 1 * direction
      return 0
    })
    return sorted
  }, [filteredSessions, sortBy, sortDirection])

  const handleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortBy(key)
    setSortDirection('asc')
  }

  const metricCell = (
    value: number | null | undefined,
    colorClass: 'bg-emerald-500' | 'bg-sky-500' | 'bg-indigo-500' | 'bg-amber-500'
  ) => {
    if (value == null || !Number.isFinite(value)) return <span className="text-gray-500">—</span>
    const percent = safePercent(value)
    return (
      <div className="flex items-center gap-2">
        <div className="w-12 h-2 bg-gray-200 rounded">
          <div className={`h-2 rounded ${colorClass}`} style={{ width: `${percent}%` }} />
        </div>
        <span className="font-medium">{percent.toFixed(0)}%</span>
      </div>
    )
  }

  const sortArrow = (key: SortKey) => {
    if (sortBy !== key) return ''
    return sortDirection === 'asc' ? ' ▲' : ' ▼'
  }

  const totalPages = Math.max(1, Math.ceil(sortedSessions.length / pageSize))
  const paginatedSessions = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return sortedSessions.slice(start, start + pageSize)
  }, [currentPage, sortedSessions])

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages)
    }
  }, [currentPage, totalPages])

  return (
    <div>
      <div className="mb-3 grid gap-3 md:grid-cols-2 lg:grid-cols-5">
        <input
          type="text"
          value={searchText}
          onChange={(event) => setSearchText(event.target.value)}
          placeholder="Search session ID..."
          className="h-9 rounded-md border border-gray-300 px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 lg:col-span-2"
        />
        <select
          value={caseFilter}
          onChange={(event) => setCaseFilter(event.target.value)}
          className="h-9 rounded-md border border-gray-300 bg-white px-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All Cases</option>
          {caseOptions.map((value) => (
            <option key={value} value={value}>
              Case {value}
            </option>
          ))}
        </select>
        <select
          value={spikesFilter}
          onChange={(event) => setSpikesFilter(event.target.value)}
          className="h-9 rounded-md border border-gray-300 bg-white px-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All SPIKES %</option>
          {spikesOptions.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <select
          value={empathyFilter}
          onChange={(event) => setEmpathyFilter(event.target.value)}
          className="h-9 rounded-md border border-gray-300 bg-white px-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All Empathy</option>
          <option value="0-25">0-25</option>
          <option value="25-50">25-50</option>
          <option value="50-75">50-75</option>
          <option value="75-100">75-100</option>
        </select>
        <select
          value={dateFilter}
          onChange={(event) => setDateFilter(event.target.value)}
          className="h-9 rounded-md border border-gray-300 bg-white px-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All Dates</option>
          <option value="24h">Last 24h</option>
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
        </select>
      </div>

      <div className="overflow-x-auto">
        <div className="max-h-[420px] overflow-y-auto border rounded-lg min-w-[980px]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b sticky top-0 bg-white z-10">
                <th className="text-left py-2">Session ID</th>
                {showExperimentMetadata && (
                  <th className="text-left py-2 cursor-pointer" onClick={() => handleSort('case')}>
                    Case{sortArrow('case')}
                  </th>
                )}
                {showExperimentMetadata && <th className="text-left py-2">Patient Model</th>}
                {showExperimentMetadata && <th className="text-left py-2">Evaluator</th>}
                {showExperimentMetadata && <th className="text-left py-2">Metrics</th>}
                <th className="text-left py-2 cursor-pointer" onClick={() => handleSort('empathy')}>
                  Empathy %{sortArrow('empathy')}
                </th>
                {showExperimentMetadata && (
                  <th className="text-left py-2 cursor-pointer" onClick={() => handleSort('communication')}>
                    Communication %{sortArrow('communication')}
                  </th>
                )}
                <th className="text-left py-2 cursor-pointer" onClick={() => handleSort('clinical')}>
                  Clinical %{sortArrow('clinical')}
                </th>
                <th className="text-left py-2 cursor-pointer" onClick={() => handleSort('spikes')}>
                  SPIKES %{sortArrow('spikes')}
                </th>
                {showExperimentMetadata && (
                  <th className="text-left py-2 cursor-pointer" onClick={() => handleSort('duration')}>
                    Duration{sortArrow('duration')}
                  </th>
                )}
                {showExperimentMetadata && <th className="text-left py-2">State</th>}
                <th className="text-left py-2 cursor-pointer" onClick={() => handleSort('date')}>
                  Date{sortArrow('date')}
                </th>
                {showActions && <th className="text-left py-2">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {paginatedSessions.map((session) => (
                <tr key={session.sessionId} className="border-b odd:bg-gray-50 hover:bg-gray-50">
                  <td className="py-2 font-mono text-xs">{session.sessionId}</td>
                  {showExperimentMetadata && <td className="py-2">{session.caseId ?? '—'}</td>}
                  {showExperimentMetadata && (
                    <td
                      title={formatPluginName(session.patientModelPlugin)}
                      className="py-2 max-w-[160px] truncate"
                    >
                      {formatPluginName(session.patientModelPlugin)}
                    </td>
                  )}
                  {showExperimentMetadata && (
                    <td
                      title={formatPluginName(session.evaluatorPlugin)}
                      className="py-2 max-w-[160px] truncate"
                    >
                      {formatPluginName(session.evaluatorPlugin)}
                    </td>
                  )}
                  {showExperimentMetadata && (
                    <td
                      title={formatMetricsPlugins(session.metricsPlugins)}
                      className="py-2 max-w-[160px] truncate"
                    >
                      {formatMetricsPlugins(session.metricsPlugins)}
                    </td>
                  )}
                  <td className="py-2">{metricCell(session.scores.empathy, 'bg-emerald-500')}</td>
                  {showExperimentMetadata && (
                    <td className="py-2">{metricCell(session.scores.communication, 'bg-sky-500')}</td>
                  )}
                  <td className="py-2">{metricCell(session.scores.clinical, 'bg-indigo-500')}</td>
                  <td className="py-2">{metricCell(getSpikesPercent(session), 'bg-amber-500')}</td>
                  {showExperimentMetadata && (
                    <td className="py-2">{formatDuration(session.duration_seconds)}</td>
                  )}
                  {showExperimentMetadata && (
                    <td className="py-2 capitalize">{session.state ?? '—'}</td>
                  )}
                  <td className="py-2 text-xs text-gray-500">
                    {formatTimestamp(session.timestamp)}
                  </td>
                  {showActions && (
                    <td className="py-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleExportSessionTranscript(session.sessionId)}
                        disabled={exportingSessionId === session.sessionId}
                      >
                        {exportingSessionId === session.sessionId
                          ? 'Exporting…'
                          : 'Export Transcript'}
                      </Button>
                    </td>
                  )}
                </tr>
              ))}
              {paginatedSessions.length === 0 && (
                <tr>
                  <td
                    colSpan={
                      (showExperimentMetadata ? 11 : 4) +
                      (showActions ? 1 : 0) +
                      1
                    }
                    className="py-6 text-center text-gray-500"
                  >
                    No sessions match your current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-sm text-gray-600">
        <span>
          Showing {sortedSessions.length === 0 ? 0 : (currentPage - 1) * pageSize + 1}-
          {Math.min(currentPage * pageSize, sortedSessions.length)} of {sortedSessions.length}
        </span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
            disabled={currentPage === 1}
          >
            Previous
          </Button>
          <span className="text-xs text-gray-500">
            Page {currentPage} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
            disabled={currentPage === totalPages}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}

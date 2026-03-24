import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { TraineeSessionAnalytics } from '@/types/analytics'
import { formatPercent } from '@/utils/format'
import { ANALYTICS_METRICS } from '@/components/analytics/analyticsMetricConfig'

type SortKey =
  | 'caseTitle'
  | 'empathyScore'
  | 'communicationScore'
  | 'clinicalScore'
  | 'spikesCoveragePercent'
  | 'createdAt'

type SortDirection = 'asc' | 'desc'

type RangeOption = 'all' | '0-25' | '25-50' | '50-75' | '75-100'

const PAGE_SIZE = 10

const rangeOptions: Array<{ value: RangeOption; label: string }> = [
  { value: 'all', label: 'All' },
  { value: '0-25', label: '0-25' },
  { value: '25-50', label: '25-50' },
  { value: '50-75', label: '50-75' },
  { value: '75-100', label: '75-100' },
]

const inRange = (value: number, range: RangeOption) => {
  if (range === 'all') return true
  if (range === '0-25') return value >= 0 && value < 25
  if (range === '25-50') return value >= 25 && value < 50
  if (range === '50-75') return value >= 50 && value < 75
  return value >= 75 && value <= 100
}

const metricBar = (value: number, colorClass: string) => {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div className="min-w-[150px]">
      <div className="mb-1 text-xs font-medium text-gray-700">{formatPercent(clamped)}</div>
      <div className="h-2.5 w-full rounded-full bg-gray-200/90">
        <div className={`h-2.5 rounded-full ${colorClass}`} style={{ width: `${clamped}%` }} />
      </div>
    </div>
  )
}

export const AnalyticsSessionsTable = ({ sessions }: { sessions: TraineeSessionAnalytics[] }) => {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [selectedCase, setSelectedCase] = useState('all')
  const [empathyRange, setEmpathyRange] = useState<RangeOption>('all')
  const [spikesRange, setSpikesRange] = useState<RangeOption>('all')
  const [sortKey, setSortKey] = useState<SortKey>('createdAt')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [page, setPage] = useState(1)

  const caseOptions = useMemo(() => {
    return [...new Set(sessions.map((s) => s.caseTitle))].sort((a, b) => a.localeCompare(b))
  }, [sessions])

  const filteredSessions = useMemo(() => {
    const term = search.trim().toLowerCase()
    return sessions.filter((s) => {
      const matchesSearch = term.length === 0 || s.caseTitle.toLowerCase().includes(term)
      const matchesCase = selectedCase === 'all' || s.caseTitle === selectedCase
      const matchesEmpathy = inRange(s.empathyScore, empathyRange)
      const matchesSpikes = inRange(s.spikesCoveragePercent, spikesRange)
      return matchesSearch && matchesCase && matchesEmpathy && matchesSpikes
    })
  }, [sessions, search, selectedCase, empathyRange, spikesRange])

  const sortedSessions = useMemo(() => {
    const items = [...filteredSessions]
    items.sort((a, b) => {
      let left: string | number = ''
      let right: string | number = ''

      switch (sortKey) {
        case 'caseTitle':
          left = a.caseTitle.toLowerCase()
          right = b.caseTitle.toLowerCase()
          break
        case 'empathyScore':
          left = a.empathyScore
          right = b.empathyScore
          break
        case 'communicationScore':
          left = a.communicationScore
          right = b.communicationScore
          break
        case 'clinicalScore':
          left = a.clinicalScore
          right = b.clinicalScore
          break
        case 'spikesCoveragePercent':
          left = a.spikesCoveragePercent
          right = b.spikesCoveragePercent
          break
        case 'createdAt':
          left = new Date(a.createdAt).getTime()
          right = new Date(b.createdAt).getTime()
          break
      }

      // Stable newest-first tie-breaker for equal timestamps
      if (sortKey === 'createdAt' && left === right) {
        return sortDirection === 'asc'
          ? a.sessionId - b.sessionId
          : b.sessionId - a.sessionId
      }

      if (left < right) return sortDirection === 'asc' ? -1 : 1
      if (left > right) return sortDirection === 'asc' ? 1 : -1
      return 0
    })
    return items
  }, [filteredSessions, sortKey, sortDirection])

  const totalPages = Math.max(1, Math.ceil(sortedSessions.length / PAGE_SIZE))

  const paginatedSessions = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE
    return sortedSessions.slice(start, start + PAGE_SIZE)
  }, [sortedSessions, page])

  useEffect(() => {
    if (page > totalPages) setPage(totalPages)
  }, [page, totalPages])

  const onSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setSortDirection(key === 'caseTitle' ? 'asc' : 'desc')
  }

  const sortArrow = (key: SortKey) => {
    if (sortKey !== key) return '↕'
    return sortDirection === 'asc' ? '↑' : '↓'
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Session History</h3>
          <p className="text-sm text-gray-500">
            Showing {paginatedSessions.length} of {filteredSessions.length} sessions
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="Search by case title"
            className="h-9 rounded-md border border-gray-300 px-3 text-sm"
          />
          <select
            value={selectedCase}
            onChange={(e) => {
              setSelectedCase(e.target.value)
              setPage(1)
            }}
            className="h-9 rounded-md border border-gray-300 px-2 text-sm"
          >
            <option value="all">All Cases</option>
            {caseOptions.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <select
            value={empathyRange}
            onChange={(e) => {
              setEmpathyRange(e.target.value as RangeOption)
              setPage(1)
            }}
            className="h-9 rounded-md border border-gray-300 px-2 text-sm"
          >
            {rangeOptions.map((r) => (
              <option key={r.value} value={r.value}>
                Empathy {r.label}
              </option>
            ))}
          </select>
          <select
            value={spikesRange}
            onChange={(e) => {
              setSpikesRange(e.target.value as RangeOption)
              setPage(1)
            }}
            className="h-9 rounded-md border border-gray-300 px-2 text-sm"
          >
            {rangeOptions.map((r) => (
              <option key={r.value} value={r.value}>
                SPIKES {r.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <div className="max-h-[460px] overflow-y-auto">
          <table className="min-w-[980px] w-full text-sm">
            <thead className="sticky top-0 z-10 bg-gray-50">
              <tr className="border-b text-gray-600">
                <th className="px-4 py-3 text-left">Session</th>
                <th className="px-4 py-3 text-left">
                  <button type="button" onClick={() => onSort('caseTitle')} className="font-semibold">
                    Case {sortArrow('caseTitle')}
                  </button>
                </th>
                <th className="px-4 py-3 text-left">
                  <button type="button" onClick={() => onSort('empathyScore')} className="font-semibold">
                    Empathy % {sortArrow('empathyScore')}
                  </button>
                </th>
                <th className="px-4 py-3 text-left">
                  <button type="button" onClick={() => onSort('communicationScore')} className="font-semibold">
                    Communication % {sortArrow('communicationScore')}
                  </button>
                </th>
                <th className="px-4 py-3 text-left">
                  <button type="button" onClick={() => onSort('clinicalScore')} className="font-semibold">
                    {ANALYTICS_METRICS.clinicalReasoning.shortLabel} % {sortArrow('clinicalScore')}
                  </button>
                </th>
                <th className="px-4 py-3 text-left">
                  <button type="button" onClick={() => onSort('spikesCoveragePercent')} className="font-semibold">
                    SPIKES % {sortArrow('spikesCoveragePercent')}
                  </button>
                </th>
                <th className="px-4 py-3 text-left">
                  <button type="button" onClick={() => onSort('createdAt')} className="font-semibold">
                    Date {sortArrow('createdAt')}
                  </button>
                </th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedSessions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-gray-500">
                    No sessions match your filters.
                  </td>
                </tr>
              ) : (
                paginatedSessions.map((s, index) => (
                  <tr
                    key={s.sessionId}
                    className={`${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/60'} border-b hover:bg-blue-50/50`}
                  >
                    <td className="px-4 py-3 font-medium text-gray-900">#{s.sessionId}</td>
                    <td className="px-4 py-3">{s.caseTitle}</td>
                    <td className="px-4 py-3">{metricBar(s.empathyScore, 'bg-blue-500')}</td>
                    <td className="px-4 py-3">{metricBar(s.communicationScore, 'bg-purple-500')}</td>
                    <td className="px-4 py-3">{metricBar(s.clinicalScore, 'bg-green-500')}</td>
                    <td className="px-4 py-3">{metricBar(s.spikesCoveragePercent, 'bg-orange-500')}</td>
                    <td className="px-4 py-3 text-gray-600">{new Date(s.createdAt).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => navigate(`/feedback/${s.sessionId}`)}
                        className="rounded-md border border-blue-200 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-50"
                      >
                        View Feedback
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
          className="rounded-md border px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
        >
          Previous
        </button>
        <span className="text-sm text-gray-600">
          Page {page} of {totalPages}
        </span>
        <button
          type="button"
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page === totalPages}
          className="rounded-md border px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  )
}


import { useState } from 'react'
import { Button } from '@/components/ui/button'
import type { ResearchData } from '@/api/research.api'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type Session = ResearchData['anonymizedSessions'][number]

type ResearchSessionsTableProps = {
  sessions: Session[]
  showActions?: boolean
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

export function ResearchSessionsTable({
  sessions,
  showActions = false,
}: ResearchSessionsTableProps) {
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

  return (
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
            {showActions && <th className="text-left py-2">Actions</th>}
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => (
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
              <td className="py-2 capitalize">{session.spikes_stage ?? '—'}</td>
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
              {showActions && (
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
  )
}

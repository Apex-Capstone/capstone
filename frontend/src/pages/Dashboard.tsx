import { useEffect, useState } from 'react'
import { listCases } from '@/api/cases.api'
import { createSession, listUserSessions } from '@/api/sessions.api'
import type { Case } from '@/types/case'
import type { Session } from '@/types/session'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'
import { CaseCard } from '@/components/CaseCard'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { useAuthStore } from '@/store/authStore'

export const Dashboard = () => {
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)
  const [sessions, setSessions] = useState<Session[]>([])
  const [creatingSessionForCase, setCreatingSessionForCase] = useState<number | null>(null)
  const { user } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        const [casesResult, sessionsResult] = await Promise.allSettled([
          listCases(),
          listUserSessions({ limit: 6 }),
        ])
        if (casesResult.status === 'fulfilled') {
          setCases(casesResult.value.items)
        } else {
          console.error('Failed to fetch cases:', casesResult.reason)
        }
        if (sessionsResult.status === 'fulfilled') {
          setSessions(sessionsResult.value.sessions)
        } else {
          console.error('Failed to fetch sessions:', sessionsResult.reason)
        }
      } finally {
        setLoading(false)
      }
    }
    loadDashboardData()
  }, [])

  const formatDurationLabel = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    if (mins > 0) {
      return `${mins}m ${secs}s`
    }
    return `${secs}s`
  }

  const handleStartNewSession = async (caseId: number) => {
    setCreatingSessionForCase(caseId)
    try {
      const session = await createSession(caseId, { forceNew: true })
      navigate(`/case/${caseId}?sessionId=${session.id}`)
    } catch (error) {
      console.error('Failed to start a new session:', error)
    } finally {
      setCreatingSessionForCase(null)
    }
  }

  const activeSessions = sessions.filter((s) => s.status === 'active')
  const closedSessions = sessions.filter((s) => s.status === 'closed')

  // derive soft status counts (since BE Case has no status)
  const statusCounts = cases.reduce(
    (acc, c) => {
      const s = (c as any)?.status ?? 'pending'
      acc[s] = (acc[s] || 0) + 1
      return acc
    },
    {} as Record<'completed' | 'in_progress' | 'pending' | string, number>
  )

  const sessionCardGrid = (sessionList: Session[]) => (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {sessionList.map((session) => {
        const isClosed = session.status === 'closed'
        const badgeText = isClosed ? 'Closed' : 'Active'
        const badgeStyles = isClosed
          ? 'bg-gray-100 border border-gray-200 text-gray-600'
          : 'bg-emerald-50 border border-emerald-200 text-emerald-700'
        return (
          <div key={session.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Session {session.id}
                </p>
                <p className="text-base font-semibold text-gray-900">
                  {session.caseTitle ?? `Case #${session.caseId}`}
                </p>
                <p className="text-xs text-gray-500">
                  Started {new Date(session.startedAt).toLocaleString()}
                </p>
              </div>
              <span
                className={`px-3 py-1 text-[10px] font-semibold uppercase rounded-full ${badgeStyles}`}
              >
                {badgeText}
              </span>
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
              <span className="capitalize">{session.state.replace('_', ' ')}</span>
              {session.endedAt ? (
                <span>Duration: {formatDurationLabel(session.durationSeconds)}</span>
              ) : (
                <span>Live</span>
              )}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {!isClosed && (
                <Button
                  size="sm"
                  variant="success"
                  onClick={() => navigate(`/case/${session.caseId}?sessionId=${session.id}`)}
                >
                  Continue
                </Button>
              )}
              {isClosed && (
                <Button
                  size="sm"
                  variant="success"
                  onClick={() => navigate(`/feedback/${session.id}`)}
                >
                  View Feedback
                </Button>
              )}
              <Button
                size="sm"
                variant="neutral"
                onClick={() => handleStartNewSession(session.caseId)}
                disabled={creatingSessionForCase === session.caseId}
              >
                Start new session
              </Button>
            </div>
          </div>
        )
      })}
    </div>
  )

  return (
    <div className="h-screen flex flex-col">
      <Navbar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 overflow-y-auto md:ml-64">
          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            <nav className="mb-4 text-sm text-gray-500">Dashboard</nav>

            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900">
                Welcome back, {user?.name || (user as any)?.full_name || user?.email}
              </h1>
              <p className="mt-2 text-gray-600">
                Practice delivering difficult news using the SPIKES communication framework
              </p>
              <div className="mt-4 flex items-center gap-4 text-sm">
                <span className="font-medium text-gray-700">Role:</span>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-800 font-medium">
                  {user?.role}
                </span>
                {user?.role === 'admin' && (
                  <span className="text-gray-500">• You have access to admin features</span>
                )}
              </div>
            </div>

            {loading ? (
              <div>
                <div className="mb-6">
                  <div className="h-6 w-48 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded animate-pulse mb-2" />
                  <div className="h-4 w-64 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded animate-pulse" />
                </div>
                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                  {[1, 2, 3, 4, 5, 6].map((n) => (
                    <div key={n} className="bg-white border rounded-lg p-6 animate-pulse">
                      <div className="flex justify-between items-start mb-4">
                        <div className="h-5 w-32 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded" />
                        <div className="h-5 w-14 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded-full" />
                      </div>
                      <div className="space-y-2 mb-4">
                        <div className="h-4 w-full bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded" />
                        <div className="h-4 w-3/4 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded" />
                      </div>
                      <div className="flex justify-between items-center">
                        <div className="h-3 w-24 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded" />
                        <div className="h-3 w-20 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                {/* Active Practice Sessions */}
                <div className="mb-8">
                  <div className="flex items-start justify-between gap-6 mb-4">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900 mb-1">Active Practice Sessions</h2>
                      <p className="text-sm text-gray-600">
                        Sessions in progress. Continue where you left off or start a new one.
                      </p>
                    </div>
                    {activeSessions.length > 0 && (
                      <span className="text-sm font-medium text-gray-500">
                        {activeSessions.length} {activeSessions.length === 1 ? 'session' : 'sessions'}
                      </span>
                    )}
                  </div>
                  {activeSessions.length === 0 ? (
                    <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-sm text-gray-500">
                      No active sessions. Start a new one.
                    </div>
                  ) : (
                    sessionCardGrid(activeSessions)
                  )}
                </div>

                {/* Closed Sessions */}
                <div className="mb-8">
                  <div className="flex items-start justify-between gap-6 mb-4">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900 mb-1">Closed Sessions</h2>
                      <p className="text-sm text-gray-600">
                        Completed simulation runs. Review feedback to improve your practice.
                      </p>
                    </div>
                    {closedSessions.length > 0 && (
                      <span className="text-sm font-medium text-gray-500">
                        {closedSessions.length} {closedSessions.length === 1 ? 'session' : 'sessions'}
                      </span>
                    )}
                  </div>
                  {closedSessions.length === 0 ? (
                    <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-sm text-gray-500">
                      No closed sessions yet.
                    </div>
                  ) : (
                    sessionCardGrid(closedSessions)
                  )}
                </div>

                {cases.length === 0 ? (
                  <div className="rounded-lg border border-gray-200 bg-white p-12 text-center">
                    <p className="text-gray-500">No virtual patient cases available. Contact your administrator.</p>
                  </div>
                ) : (
                  <div>
                    <div className="mb-6">
                      <h2 className="text-xl font-semibold text-gray-900 mb-2">Virtual Patient Cases</h2>
                      <p className="text-gray-600">
                        Select a case to practice your communication skills using the SPIKES framework
                      </p>
                    </div>

                    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                      {cases.map((caseItem) => (
                        <CaseCard key={caseItem.id} caseData={caseItem as any} />
                      ))}
                    </div>

                    {/* Quick stats (tolerant if status doesn't exist) */}
                    <div className="mt-12 grid gap-4 sm:grid-cols-3">
                      <div className="bg-white rounded-lg border p-4 text-center">
                        <div className="text-2xl font-bold text-emerald-600">
                          {statusCounts['completed'] ?? 0}
                        </div>
                        <div className="text-sm text-gray-600">Completed Cases</div>
                      </div>
                      <div className="bg-white rounded-lg border p-4 text-center">
                        <div className="text-2xl font-bold text-orange-600">
                          {statusCounts['in_progress'] ?? 0}
                        </div>
                        <div className="text-sm text-gray-600">In Progress</div>
                      </div>
                      <div className="bg-white rounded-lg border p-4 text-center">
                        <div className="text-2xl font-bold text-gray-600">
                          {statusCounts['pending'] ?? cases.length}
                        </div>
                        <div className="text-sm text-gray-600">Available</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

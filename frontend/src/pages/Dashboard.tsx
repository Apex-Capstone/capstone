import { useEffect, useState } from 'react'
import { closeSession, listActiveSessions, listCompletedSessions } from '@/api/sessions.api'
import { fetchMySessionAnalytics } from '@/api/analytics.api'
import type { Session } from '@/types/session'
import { Button } from '@/components/ui/button'
import { StatsCard } from '@/components/StatsCard'
import { useNavigate } from 'react-router-dom'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { useAuthStore } from '@/store/authStore'
import { toast } from 'sonner'
import { Activity, BarChart3, CheckCircle2, ClipboardList, HeartHandshake } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'

export const Dashboard = () => {
  const [loading, setLoading] = useState(true)
  const [activeSessions, setActiveSessions] = useState<Session[]>([])
  const [activeTotal, setActiveTotal] = useState(0)
  const [completedSessions, setCompletedSessions] = useState<Session[]>([])
  const [completedTotal, setCompletedTotal] = useState(0)
  const [closingSessionId, setClosingSessionId] = useState<number | null>(null)
  const [confirmCloseSession, setConfirmCloseSession] = useState<Session | null>(null)
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const totalSessions = activeTotal + completedTotal
  const [avgEmpathy, setAvgEmpathy] = useState<number | null>(null)
  const [avgSpikesCoverageStageCount, setAvgSpikesCoverageStageCount] = useState<number | null>(null)

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        const [activeResult, completedResult, analyticsResult] = await Promise.allSettled([
          listActiveSessions({ limit: 3 }),
          listCompletedSessions({ limit: 3 }),
          fetchMySessionAnalytics(),
        ])
        if (activeResult.status === 'fulfilled') {
          setActiveSessions(activeResult.value.sessions ?? [])
          setActiveTotal(activeResult.value.total ?? 0)
        } else {
          console.error('Failed to fetch active sessions:', activeResult.reason)
        }
        if (completedResult.status === 'fulfilled') {
          setCompletedSessions(completedResult.value.sessions ?? [])
          setCompletedTotal(completedResult.value.total ?? 0)
        } else {
          console.error('Failed to fetch completed sessions:', completedResult.reason)
        }

        if (analyticsResult.status === 'fulfilled') {
          const analytics = analyticsResult.value
          const empathyValues = analytics
            .map((a) => (typeof a.empathyScore === 'number' && Number.isFinite(a.empathyScore) ? a.empathyScore : null))
            .filter((v): v is number => v != null)

          const stagesValues = analytics
            .map((a) => spikesStageCountFromAnalytics(a))
            .filter((v): v is number => v != null)

          const empathyAvg = empathyValues.length ? empathyValues.reduce((s, v) => s + v, 0) / empathyValues.length : null
          const spikesAvg = stagesValues.length ? stagesValues.reduce((s, v) => s + v, 0) / stagesValues.length : null

          setAvgEmpathy(empathyAvg)
          setAvgSpikesCoverageStageCount(spikesAvg)
        } else {
          setAvgEmpathy(null)
          setAvgSpikesCoverageStageCount(null)
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

  const SPIKES_TOTAL_STAGES = 6

  const clampStageCount = (stageCount: number) => {
    if (!Number.isFinite(stageCount)) return 0
    return Math.max(0, Math.min(SPIKES_TOTAL_STAGES, Math.round(stageCount)))
  }

  const spikesStageCountFromAnalytics = (analytics: {
    spikesStagesCovered?: string[]
    spikesCoveragePercent: number
  }): number | null => {
    if (analytics.spikesStagesCovered?.length) {
      return clampStageCount(analytics.spikesStagesCovered.length)
    }
    const pct = analytics.spikesCoveragePercent
    if (typeof pct === 'number' && Number.isFinite(pct)) {
      return clampStageCount((pct / 100) * SPIKES_TOTAL_STAGES)
    }
    return null
  }

  const handleStartNewSession = async () => {
    navigate('/cases')
  }

  const handleCloseSession = async () => {
    if (!confirmCloseSession) return
    const session = confirmCloseSession
    setConfirmCloseSession(null)
    setClosingSessionId(session.id)
    try {
      await closeSession(session.id)
      setActiveSessions((prev) => prev.filter((s) => s.id !== session.id))
      setActiveTotal((prev) => Math.max(prev - 1, 0))
      setCompletedSessions((prev) => [{ ...session, status: 'closed' as const, state: 'completed' }, ...prev].slice(0, 3))
      setCompletedTotal((prev) => prev + 1)
      toast.success(`Session ${session.id} closed — ${session.caseTitle ?? `Case #${session.caseId}`}`)
    } catch (error) {
      console.error('Failed to close session:', error)
      toast.error('Failed to close session. Please try again.')
    } finally {
      setClosingSessionId(null)
    }
  }

  const activeSessionCard = (session: Session) => (
    <div key={session.id} className="rounded-lg border border-gray-200 border-l-4 border-l-emerald-500 bg-white p-4 transition-shadow hover:shadow-md hover:border-emerald-300">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-base font-semibold text-gray-900">
            {session.caseTitle ?? `Case #${session.caseId}`}
          </p>
          <p className="mt-0.5 text-xs text-gray-400">
            Session {session.id} · Started {new Date(session.startedAt).toLocaleString()}
          </p>
        </div>
        <span className="px-3 py-1 text-[10px] font-semibold uppercase rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700">
          Active
        </span>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="success"
          onClick={() => navigate(`/case/${session.caseId}?sessionId=${session.id}`)}
        >
          Continue
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="text-rose-600 border-rose-200 hover:bg-rose-50 hover:text-rose-700"
          onClick={() => setConfirmCloseSession(session)}
          disabled={closingSessionId === session.id}
        >
          {closingSessionId === session.id ? 'Closing...' : 'Close Session'}
        </Button>
      </div>
    </div>
  )

  const completedSessionCard = (session: Session) => (
    <div key={session.id} className="rounded-lg border border-gray-200 border-l-4 border-l-gray-300 bg-white p-4 transition-shadow hover:shadow-md hover:border-gray-300">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-base font-semibold text-gray-900">
            {session.caseTitle ?? `Case #${session.caseId}`}
          </p>
          <p className="mt-0.5 text-xs text-gray-400">
            Session {session.id} · {formatDurationLabel(session.durationSeconds ?? 0)}
          </p>
        </div>
        <span className="px-3 py-1 text-[10px] font-semibold uppercase rounded-full bg-gray-100 border border-gray-200 text-gray-600">
          Completed
        </span>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="success"
          onClick={() => navigate(`/feedback/${session.id}`)}
        >
          View Feedback
        </Button>
      </div>
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
                Welcome back, {user?.full_name || user?.email}
              </h1>
              <p className="mt-2 text-gray-600">
                Practice delivering difficult news using the SPIKES communication framework
              </p>
              <div className="mt-4 flex items-center gap-4 text-sm">
                <span className="font-medium text-gray-700">Role:</span>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-800 font-medium">
                  {user?.role && user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                </span>
                {user?.role === 'admin' && (
                  <span className="text-gray-500">• You have access to admin features</span>
                )}
              </div>
            </div>

            {loading ? (
              <div>
                <div className="mb-8">
                  <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-5 gap-4">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <div key={n} className="h-20 rounded-lg bg-gray-200 animate-pulse" />
                    ))}
                  </div>
                </div>
                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                  {[1, 2, 3, 4, 5, 6].map((n) => (
                    <div key={n} className="rounded-lg bg-gray-200 p-6 animate-pulse">
                      <div className="flex justify-between items-start mb-4">
                        <div className="h-5 w-32 bg-gray-200 rounded" />
                        <div className="h-5 w-14 bg-gray-200 rounded-full" />
                      </div>
                      <div className="space-y-2 mb-4">
                        <div className="h-4 w-full bg-gray-200 rounded" />
                        <div className="h-4 w-3/4 bg-gray-200 rounded" />
                      </div>
                      <div className="flex justify-between items-center">
                        <div className="h-3 w-24 bg-gray-200 rounded" />
                        <div className="h-3 w-20 bg-gray-200 rounded" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                <div className="mb-8">
                  <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-5 gap-4">
                    <StatsCard
                      icon={ClipboardList}
                      title="Total Sessions"
                      value={totalSessions}
                    />
                    <StatsCard
                      icon={Activity}
                      title="Active Sessions"
                      value={activeTotal}
                      valueClassName="text-emerald-700"
                    />
                    <StatsCard
                      icon={CheckCircle2}
                      title="Completed Sessions"
                      value={completedTotal}
                      valueClassName="text-gray-700"
                    />
                    <StatsCard
                      icon={HeartHandshake}
                      title="Average Empathy Score"
                      value={avgEmpathy == null ? '—' : Math.round(avgEmpathy)}
                    />
                    <StatsCard
                      icon={BarChart3}
                      title="Average SPIKES Coverage"
                      value={
                        avgSpikesCoverageStageCount == null
                          ? '—'
                          : `${avgSpikesCoverageStageCount.toFixed(1)} / 6`
                      }
                    />
                  </div>
                </div>

                {/* Quick actions */}
                <div className="mb-8">
                  <div className="flex flex-wrap items-center gap-3">
                    <Button variant="success" onClick={handleStartNewSession}>
                      Start New Session
                    </Button>
                    <Button variant="outline" onClick={() => navigate('/sessions')}>
                      View My Sessions
                    </Button>
                    <Button variant="outline" onClick={() => navigate('/analytics')}>
                      View Analytics
                    </Button>
                  </div>
                </div>

                {/* Sessions */}
                <div className="mb-8">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-semibold text-gray-900">Sessions</h2>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate('/sessions')}
                    >
                      View all sessions
                    </Button>
                  </div>

                  {/* Active */}
                  <div className="mb-6">
                    <h3 className="text-base font-medium text-gray-800 mb-3 flex items-center gap-2">
                      Active
                    </h3>
                    {activeSessions.length === 0 ? (
                      <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-sm text-gray-500">
                        No active sessions. Start a new one below.
                      </div>
                    ) : (
                      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        {activeSessions.map(activeSessionCard)}
                      </div>
                    )}
                  </div>

                  {/* Completed */}
                  <div>
                    <h3 className="text-base font-medium text-gray-800 mb-3 flex items-center gap-2">
                      Completed
                    </h3>
                    {completedSessions.length === 0 ? (
                      <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-sm text-gray-500">
                        No completed sessions yet.
                      </div>
                    ) : (
                      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        {completedSessions.map(completedSessionCard)}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>

      <Dialog open={!!confirmCloseSession} onOpenChange={(open) => { if (!open) setConfirmCloseSession(null) }}>
        <DialogContent className="sm:max-w-md [&>button:last-child]:hidden">
          <DialogHeader>
            <DialogTitle>Close Session?</DialogTitle>
            <DialogDescription>
              Are you sure you want to close{' '}
              <span className="font-medium text-gray-900">
                Session {confirmCloseSession?.id}
              </span>
              {' '}of{' '}
              <span className="font-medium text-gray-900">
                {confirmCloseSession?.caseTitle ?? `Case #${confirmCloseSession?.caseId}`}
              </span>
              {`? This will end the session and generate feedback. You won't be able to continue it afterward.`}
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 flex justify-end gap-3">
            <Button variant="outline" size="sm" onClick={() => setConfirmCloseSession(null)}>
              Cancel
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={handleCloseSession}
            >
              Close Session
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

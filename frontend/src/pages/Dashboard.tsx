import { useEffect, useState } from 'react'
import { closeSession, listActiveSessions, listCompletedSessions } from '@/api/sessions.api'
import { fetchMySessionAnalytics } from '@/api/analytics.api'
import type { Session } from '@/types/session'
import type { TraineeSessionAnalytics } from '@/types/analytics'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { StatsCard } from '@/components/StatsCard'
import { useNavigate } from 'react-router-dom'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { useAuthStore } from '@/store/authStore'
import { toast } from 'sonner'
import {
  Activity,
  BarChart3,
  CheckCircle2,
  ClipboardList,
  HeartHandshake,
  Lightbulb,
  TrendingUp,
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'

const SPIKES_TOTAL_STAGES = 6

function clampStageCount(stageCount: number) {
  if (!Number.isFinite(stageCount)) return 0
  return Math.max(0, Math.min(SPIKES_TOTAL_STAGES, Math.round(stageCount)))
}

function spikesStageCountFromAnalytics(a: {
  spikesStagesCovered?: string[]
  spikesCoveragePercent: number
}): number | null {
  if (a.spikesStagesCovered?.length) return clampStageCount(a.spikesStagesCovered.length)
  const pct = a.spikesCoveragePercent
  if (typeof pct === 'number' && Number.isFinite(pct)) return clampStageCount((pct / 100) * SPIKES_TOTAL_STAGES)
  return null
}

function formatDurationLabel(seconds: number) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  if (mins === 0) return `${secs}s`
  if (secs === 0) return `${mins}m`
  return `${mins}m ${secs}s`
}

function computeInsight(analytics: TraineeSessionAnalytics[]): string | null {
  if (analytics.length === 0) return null
  const avgEmpathy = analytics.reduce((s, a) => s + a.empathyScore, 0) / analytics.length
  const avgSpikes = analytics.reduce((s, a) => s + a.spikesCoveragePercent, 0) / analytics.length

  if (avgEmpathy >= 80 && avgSpikes >= 80) {
    return 'Excellent performance across both empathy and SPIKES coverage. Keep up the great work!'
  }
  if (avgEmpathy >= 80) {
    return 'Your empathy scores are consistently strong. Focus on covering more SPIKES stages to round out your communication skills.'
  }
  if (avgSpikes >= 80) {
    return 'Great SPIKES coverage! Consider focusing on empathetic responses to further improve patient interactions.'
  }
  if (avgEmpathy < 60) {
    return 'You consistently acknowledge patient emotions, but could improve empathy follow-up responses.'
  }
  return 'Practice consistently to improve your empathy scores and SPIKES coverage across sessions.'
}

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
  const [allAnalytics, setAllAnalytics] = useState<TraineeSessionAnalytics[]>([])

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
          const sorted = [...analytics].sort(
            (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
          )
          setAllAnalytics(sorted)

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
          setAllAnalytics([])
        }
      } finally {
        setLoading(false)
      }
    }
    loadDashboardData()
  }, [])

  const lastSession = allAnalytics[0] ?? null
  const sparklineScores = allAnalytics.slice(0, 5).reverse().map((a) => a.empathyScore)
  const sparklineTrend =
    sparklineScores.length >= 2
      ? Math.round(sparklineScores[sparklineScores.length - 1] - sparklineScores[sparklineScores.length - 2])
      : null
  const insightMessage = computeInsight(allAnalytics)

  const handleStartNewSession = () => {
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
    <div
      key={session.id}
      className="flex h-full flex-col rounded-lg border border-gray-200 border-l-4 border-l-apex-500 bg-white p-4 transition-shadow hover:border-apex-300 hover:shadow-md"
    >
      <div className="flex flex-1 items-start justify-between gap-4">
        <div>
          <p className="text-base font-semibold text-gray-900">
            {session.caseTitle ?? `Case #${session.caseId}`}
          </p>
          <p className="mt-0.5 text-sm text-gray-500">
            Session {session.id} &bull; Started {new Date(session.startedAt).toLocaleString()}
          </p>
        </div>
        <span className="rounded-full border border-apex-200 bg-apex-50 px-3 py-1 text-[10px] font-semibold uppercase text-apex-700">
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
          className="text-red-600 border-red-300 hover:bg-red-50 hover:text-red-700"
          onClick={() => setConfirmCloseSession(session)}
          disabled={closingSessionId === session.id}
        >
          {closingSessionId === session.id ? 'Closing...' : 'Close Session'}
        </Button>
      </div>
    </div>
  )

  const completedSessionCard = (session: Session) => (
    <div
      key={session.id}
      className="flex h-full cursor-pointer flex-col rounded-lg border border-gray-200 border-l-4 border-l-gray-300 bg-white p-4 transition-shadow hover:border-apex-300 hover:shadow-md"
      onClick={() => navigate(`/feedback/${session.id}`)}
      role="link"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') navigate(`/feedback/${session.id}`) }}
    >
      <div className="flex flex-1 items-start justify-between gap-4">
        <div>
          <p className="text-base font-semibold text-gray-900">
            {session.caseTitle ?? `Case #${session.caseId}`}
          </p>
          <p className="mt-0.5 text-sm text-gray-500">
            Session {session.id} &bull; {formatDurationLabel(session.durationSeconds ?? 0)}
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
          onClick={(e) => { e.stopPropagation(); navigate(`/feedback/${session.id}`) }}
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
                <span className="rounded-full bg-apex-100 px-3 py-1 font-medium text-apex-800">
                  {user?.role && user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                </span>
                {user?.role === 'admin' && (
                  <span className="text-gray-500">&bull; You have access to admin features</span>
                )}
              </div>
            </div>

            {loading ? (
              <div>
                <div className="mb-8">
                  <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-5 gap-4">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <div key={n} className="h-24 rounded-lg bg-gray-100 animate-pulse" />
                    ))}
                  </div>
                </div>
                <div className="mb-8 grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[1, 2, 3].map((n) => (
                    <div key={n} className="h-40 rounded-lg bg-gray-100 animate-pulse" />
                  ))}
                </div>
              </div>
            ) : (
              <div>
                {/* Clickable stat cards */}
                <div className="mb-8">
                  <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-5 gap-4">
                    <StatsCard
                      icon={ClipboardList}
                      title="Total Sessions"
                      value={totalSessions}
                      href="/sessions"
                      hintText="View Sessions"
                    />
                    <StatsCard
                      icon={Activity}
                      title="Active Sessions"
                      value={activeTotal}
                      valueClassName="text-2xl font-bold text-apex-700"
                      href="/sessions?filter=active"
                      hintText="View Active"
                    />
                    <StatsCard
                      icon={CheckCircle2}
                      title="Completed Sessions"
                      value={completedTotal}
                      valueClassName="text-2xl font-bold text-gray-700"
                      href="/sessions?filter=completed"
                      hintText="View Completed"
                    />
                    <StatsCard
                      icon={HeartHandshake}
                      title="Avg Empathy"
                      value={avgEmpathy == null ? '—' : `${Math.round(avgEmpathy)}%`}
                      href="/analytics"
                      hintText="View Analytics"
                    />
                    <StatsCard
                      icon={BarChart3}
                      title="Avg SPIKES"
                      value={
                        avgSpikesCoverageStageCount == null
                          ? '—'
                          : `${avgSpikesCoverageStageCount.toFixed(1)} / 6`
                      }
                      href="/analytics"
                      hintText="View Analytics"
                    />
                  </div>
                </div>

                {/* Last Session + Insight + Trend row */}
                {allAnalytics.length > 0 && (
                  <div className="mb-8 grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Last Session Performance */}
                    {lastSession && (
                      <Card className="h-full transition hover:shadow-md hover:border-apex-300">
                        <CardContent className="p-4 h-full flex flex-col justify-between">
                          <div>
                            <div className="text-sm font-semibold text-gray-500 mb-2">
                              Last Session
                            </div>
                            <div className="text-xl font-semibold text-gray-900 mb-3 truncate">
                              {lastSession.caseTitle}
                            </div>
                            <div className="grid grid-cols-2 gap-y-2 text-base mt-4">
                              <span className="text-gray-500">Empathy</span>
                              <span className="font-semibold text-gray-900 text-right">
                                {Math.round(lastSession.empathyScore)}%
                              </span>
                              <span className="text-gray-500">Communication</span>
                              <span className="font-semibold text-gray-900 text-right">
                                {Math.round(lastSession.communicationScore)}%
                              </span>
                              <span className="text-gray-500">SPIKES</span>
                              <span className="font-semibold text-gray-900 text-right">
                                {spikesStageCountFromAnalytics(lastSession) ?? '—'} / 6
                              </span>
                            </div>
                          </div>
                          <Button
                            variant="success"
                            className="mt-4 w-full py-2.5"
                            onClick={() => navigate(`/feedback/${lastSession.sessionId}`)}
                          >
                            View Feedback
                          </Button>
                        </CardContent>
                      </Card>
                    )}

                    {/* Training Insight */}
                    {insightMessage && (
                      <Card className="h-full transition hover:shadow-md hover:border-apex-300">
                        <CardContent className="p-4 h-full flex flex-col">
                          <div className="flex items-center gap-2 mb-2">
                            <Lightbulb className="h-5 w-5 text-amber-500" />
                            <span className="text-sm font-semibold text-gray-500">
                              Training Insight
                            </span>
                          </div>
                          <p className="text-base leading-relaxed text-gray-700 mt-2">
                            {insightMessage}
                          </p>
                          <p className="text-sm text-gray-400 mt-auto pt-3">
                            Based on your recent sessions
                          </p>
                        </CardContent>
                      </Card>
                    )}

                    {/* Performance Trend */}
                    {sparklineScores.length >= 2 && (
                      <Card className="h-full transition hover:shadow-md hover:border-apex-300">
                        <CardContent className="p-4 h-full flex flex-col justify-between">
                          <div>
                            <div className="flex items-center gap-2 mb-2">
                              <TrendingUp className="h-5 w-5 text-apex-600" />
                              <span className="text-sm font-semibold text-gray-500">
                                Empathy Trend
                              </span>
                            </div>
                            <div className="flex items-end gap-2 w-full h-24 mt-4">
                              {sparklineScores.map((score, i) => (
                                <div
                                  key={i}
                                  className="flex-1 rounded-sm bg-apex-500 transition-all"
                                  style={{ height: `${Math.max(score, 5)}%` }}
                                />
                              ))}
                            </div>
                          </div>
                          <div className="mt-2">
                            <p className="text-sm text-gray-400">Last {sparklineScores.length} sessions</p>
                            {sparklineTrend != null && (
                              <p className="text-base font-medium text-gray-600 mt-1">
                                {sparklineTrend >= 0 ? '+' : ''}
                                {sparklineTrend}% last session
                              </p>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                )}

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
                  <h2 className="text-xl font-semibold text-gray-900 mb-6">Recent Sessions</h2>

                  {/* Active */}
                  <div className="mb-6">
                    <h3 className="text-base font-medium text-gray-800 mb-3 flex items-center gap-2">
                      Active
                      {activeTotal > 0 && (
                        <span className="text-sm font-normal text-gray-500">
                          (showing {activeSessions.length} of {activeTotal})
                        </span>
                      )}
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
                      {completedTotal > 0 && (
                        <span className="text-sm font-normal text-gray-500">
                          (showing {completedSessions.length} of {completedTotal})
                        </span>
                      )}
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

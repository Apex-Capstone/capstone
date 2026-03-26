import { useEffect, useState, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { listActiveSessions, listCompletedSessions, closeSession } from '@/api/sessions.api'
import { getCase } from '@/api/cases.api'
import { fetchMySessionAnalytics } from '@/api/analytics.api'
import type { Session } from '@/types/session'
import type { Case } from '@/types/case'
import type { TraineeSessionAnalytics } from '@/types/analytics'
import { SessionCard } from '@/components/SessionCard'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ClipboardList, BookOpen } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { toast } from 'sonner'

type FilterState = 'all' | 'active' | 'completed'

const VALID_FILTERS: FilterState[] = ['all', 'active', 'completed']

function isValidFilter(v: string | null): v is FilterState {
  return v != null && VALID_FILTERS.includes(v as FilterState)
}

export const Sessions = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialFilter = isValidFilter(searchParams.get('filter')) ? (searchParams.get('filter') as FilterState) : 'all'

  const [sessions, setSessions] = useState<Session[]>([])
  const [caseMap, setCaseMap] = useState<Record<number, Case>>({})
  const [analyticsBySessionId, setAnalyticsBySessionId] = useState<
    Record<number, TraineeSessionAnalytics>
  >({})
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<FilterState>(initialFilter)
  const [closingSessionId, setClosingSessionId] = useState<number | null>(null)
  const [confirmCloseSession, setConfirmCloseSession] = useState<Session | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const [activeResult, completedResult, analyticsResult] = await Promise.allSettled([
          listActiveSessions(),
          listCompletedSessions(),
          fetchMySessionAnalytics(),
        ])
        const all: Session[] = []
        if (activeResult.status === 'fulfilled') all.push(...activeResult.value.sessions)
        if (completedResult.status === 'fulfilled') all.push(...completedResult.value.sessions)
        setSessions(all)

        if (analyticsResult.status === 'fulfilled') {
          const map: Record<number, TraineeSessionAnalytics> = {}
          analyticsResult.value.forEach((a) => {
            map[a.sessionId] = a
          })
          setAnalyticsBySessionId(map)
        } else {
          setAnalyticsBySessionId({})
        }

        const caseIds = [...new Set(all.map((s) => s.caseId))]
        const cases = await Promise.all(
          caseIds.map((id) => getCase(id).catch(() => null))
        )
        const map: Record<number, Case> = {}
        cases.forEach((c) => {
          if (c) map[c.id] = c
        })
        setCaseMap(map)
      } catch (err) {
        console.error('Failed to load sessions:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleCloseSession = async () => {
    if (!confirmCloseSession) return
    const session = confirmCloseSession
    setConfirmCloseSession(null)
    setClosingSessionId(session.id)
    try {
      await closeSession(session.id)
      setSessions((prev) =>
        prev.map((s) =>
          s.id === session.id ? { ...s, state: 'completed', status: 'closed' as const } : s
        )
      )
      toast.success(`Session ${session.id} closed — ${session.caseTitle ?? caseMap[session.caseId]?.title ?? `Case #${session.caseId}`}`)
    } catch (error) {
      console.error('Failed to close session:', error)
      toast.error('Failed to close session. Please try again.')
    } finally {
      setClosingSessionId(null)
    }
  }

  const displaySessions = useMemo(() => {
    const byStartedAtDesc = (items: Session[]) =>
      [...items].sort(
        (a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime()
      )

    const active = sessions.filter((s) => s.state === 'active')
    const completed = sessions.filter((s) => s.state === 'completed')

    if (filter === 'active') return byStartedAtDesc(active)
    if (filter === 'completed') return byStartedAtDesc(completed)

    return [...byStartedAtDesc(active), ...byStartedAtDesc(completed)]
  }, [sessions, filter])

  const counts = useMemo(() => {
    const active = sessions.filter((s) => s.state === 'active').length
    const completed = sessions.filter((s) => s.state === 'completed').length
    return { active, completed, all: sessions.length }
  }, [sessions])

  const filters: { label: string; value: FilterState; count: number }[] = [
    { label: 'All', value: 'all', count: counts.all },
    { label: 'Active', value: 'active', count: counts.active },
    { label: 'Completed', value: 'completed', count: counts.completed },
  ]

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 md:ml-64">
          <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
            <nav className="mb-4 text-sm text-gray-500">
              <span
                className="cursor-pointer hover:text-gray-700"
                onClick={() => navigate('/dashboard')}
              >
                Dashboard
              </span>
              {' / '}
              <span className="text-gray-900">My Sessions</span>
            </nav>

            <div className="mb-8 flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">My Sessions</h1>
                <p className="mt-2 text-gray-600">
                  Review your past and active training sessions
                </p>
              </div>
              <Button onClick={() => navigate('/cases')} variant="outline" className="gap-2">
                <BookOpen className="h-4 w-4" />
                Browse Cases
              </Button>
            </div>

            {/* Filter bar */}
            <div className="mb-6 flex gap-2">
              {filters.map(({ label, value, count }) => (
                <button
                  key={value}
                  onClick={() => setFilter(value)}
                  className={cn(
                    'rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
                    filter === value
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  )}
                >
                  {label}
                  <span
                    className={cn(
                      'ml-1.5 rounded-full px-1.5 py-0.5 text-xs',
                      filter === value ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
                    )}
                  >
                    {count}
                  </span>
                </button>
              ))}
            </div>

            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4].map((n) => (
                  <div key={n} className="animate-pulse rounded-lg bg-gray-100 p-6">
                    <div className="flex items-center justify-between">
                      <div className="space-y-2">
                        <div className="h-5 w-48 rounded bg-gray-200" />
                        <div className="h-4 w-64 rounded bg-gray-200" />
                      </div>
                      <div className="h-8 w-24 rounded bg-gray-200" />
                    </div>
                  </div>
                ))}
              </div>
            ) : displaySessions.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center py-16 text-center">
                  <ClipboardList className="mb-4 h-12 w-12 text-gray-300" />
                  <p className="text-lg font-medium text-gray-700">
                    {filter === 'all'
                      ? 'No sessions yet'
                      : `No ${filter} sessions`}
                  </p>
                  <p className="mt-1 text-sm text-gray-500">
                    {filter === 'all'
                      ? 'Start your first clinical communication simulation to begin receiving feedback.'
                      : 'Try a different filter or start a new session.'}
                  </p>
                  <Button
                    className="mt-6"
                    variant="success"
                    onClick={() => navigate('/cases')}
                  >
                    {filter === 'all' ? 'Start Session' : 'Browse Cases'}
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3 max-h-[420px] overflow-y-auto scroll-smooth pr-1 pb-2">
                {displaySessions.map((session) => {
                  const caseTitle =
                    caseMap[session.caseId]?.title ?? session.caseTitle ?? `Case #${session.caseId}`
                  const isCompleted = session.state === 'completed'
                  const analytics = isCompleted ? analyticsBySessionId[session.id] : undefined

                  if (isCompleted) {
                    return (
                      <SessionCard
                        key={session.id}
                        session={session}
                        caseTitle={caseTitle}
                        analytics={analytics}
                        to={`/feedback/${session.id}`}
                        actions={
                          <Button size="sm" variant="success">
                            View Feedback
                          </Button>
                        }
                      />
                    )
                  }

                  return (
                    <SessionCard
                      key={session.id}
                      session={session}
                      caseTitle={caseTitle}
                      actions={
                        <>
                          <Button
                            size="sm"
                            variant="success"
                            onClick={(e) => {
                              e.stopPropagation()
                              navigate(`/case/${session.caseId}?sessionId=${session.id}`)
                            }}
                          >
                            Continue
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-red-600 border-red-300 hover:bg-red-50 hover:text-red-700"
                            disabled={closingSessionId === session.id}
                            onClick={(e) => {
                              e.stopPropagation()
                              setConfirmCloseSession(session)
                            }}
                          >
                            {closingSessionId === session.id ? 'Closing...' : 'Close Session'}
                          </Button>
                        </>
                      }
                    />
                  )
                })}
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
                {confirmCloseSession?.caseTitle ?? caseMap[confirmCloseSession?.caseId ?? 0]?.title ?? `Case #${confirmCloseSession?.caseId}`}
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

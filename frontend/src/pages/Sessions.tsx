import { useEffect, useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listSessions } from '@/api/sessions.api'
import { getCase } from '@/api/cases.api'
import type { Session } from '@/types/session'
import type { Case } from '@/types/case'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ClipboardList, Clock, CheckCircle2, ChevronRight, BookOpen } from 'lucide-react'
import { cn } from '@/lib/utils'

type FilterState = 'all' | 'active' | 'completed'

function formatDuration(seconds: number): string {
  if (seconds <= 0) return '0s'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m === 0) return `${s}s`
  return `${m}m ${s}s`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const SPIKES_DISPLAY: Record<string, string> = {
  setting: 'Setting',
  perception: 'Perception',
  invitation: 'Invitation',
  knowledge: 'Knowledge',
  empathy: 'Empathy',
  strategy: 'Strategy',
  summary: 'Strategy',
}

export const Sessions = () => {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<Session[]>([])
  const [caseMap, setCaseMap] = useState<Record<number, Case>>({})
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<FilterState>('all')

  useEffect(() => {
    const load = async () => {
      try {
        const sessionData = await listSessions()
        setSessions(sessionData.sessions)

        const caseIds = [...new Set(sessionData.sessions.map((s) => s.caseId))]
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

  const filtered = useMemo(() => {
    if (filter === 'all') return sessions
    return sessions.filter((s) => s.state === filter)
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
              <Button onClick={() => navigate('/dashboard')} variant="outline" className="gap-2">
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
                      ? 'bg-emerald-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  )}
                >
                  {label}
                  <span
                    className={cn(
                      'ml-1.5 rounded-full px-1.5 py-0.5 text-xs',
                      filter === value ? 'bg-emerald-500 text-white' : 'bg-gray-200 text-gray-500'
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
                  <div key={n} className="animate-pulse rounded-lg border bg-white p-5">
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
            ) : filtered.length === 0 ? (
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
                      ? 'Start a practice session from the Dashboard.'
                      : 'Try a different filter or start a new session.'}
                  </p>
                  <Button
                    className="mt-6"
                    onClick={() => navigate('/dashboard')}
                  >
                    Browse Cases
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {filtered
                  .slice()
                  .sort(
                    (a, b) =>
                      new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime()
                  )
                  .map((session) => {
                    const caseTitle = caseMap[session.caseId]?.title ?? `Case #${session.caseId}`
                    const isCompleted = session.state === 'completed'
                    const spikesLabel = session.currentSpikesStage
                      ? (SPIKES_DISPLAY[session.currentSpikesStage] ?? session.currentSpikesStage)
                      : null

                    return (
                      <Link
                        key={session.id}
                        to={`/sessions/${session.id}`}
                        className="group flex cursor-pointer items-center justify-between rounded-lg border bg-white p-5 transition-shadow hover:shadow-md hover:border-emerald-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 no-underline text-inherit block"
                      >
                        <div className="flex items-start gap-4">
                          <div
                            className={cn(
                              'mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full',
                              isCompleted
                                ? 'bg-emerald-100 text-emerald-600'
                                : 'bg-amber-100 text-amber-600'
                            )}
                          >
                            {isCompleted ? (
                              <CheckCircle2 className="h-5 w-5" />
                            ) : (
                              <Clock className="h-5 w-5" />
                            )}
                          </div>

                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-semibold text-gray-900">{caseTitle}</span>
                              <span
                                className={cn(
                                  'rounded-full px-2 py-0.5 text-xs font-medium',
                                  isCompleted
                                    ? 'bg-emerald-100 text-emerald-700'
                                    : 'bg-amber-100 text-amber-700'
                                )}
                              >
                                {isCompleted ? 'Completed' : 'Active'}
                              </span>
                              {spikesLabel && (
                                <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
                                  {spikesLabel}
                                </span>
                              )}
                            </div>

                            <div className="mt-1 flex items-center gap-3 text-sm text-gray-500">
                              <span>{formatDate(session.startedAt)}</span>
                              <span className="text-gray-300">•</span>
                              <span>
                                {isCompleted
                                  ? formatDuration(session.durationSeconds)
                                  : 'In progress'}
                              </span>
                              <span className="text-gray-300">•</span>
                              <span>Session #{session.id}</span>
                            </div>
                          </div>
                        </div>

                        <ChevronRight className="h-5 w-5 text-gray-300 transition-colors group-hover:text-emerald-500" />
                      </Link>
                    )
                  })}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

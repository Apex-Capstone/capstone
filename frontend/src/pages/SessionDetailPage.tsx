import { useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { getSession } from '@/api/sessions.api'
import { getCase } from '@/api/cases.api'
import { fetchFeedback } from '@/api/feedback.api'
import type { SessionDetail } from '@/types/session'
import type { Case } from '@/types/case'
import type { Feedback } from '@/api/feedback.api'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  User,
  Bot,
  CheckCircle2,
  Clock,
  Calendar,
  Timer,
  ChevronRight,
  ArrowLeft,
  Play,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const SPIKES_DISPLAY: Record<string, string> = {
  setting: 'Setting',
  perception: 'Perception',
  invitation: 'Invitation',
  knowledge: 'Knowledge',
  empathy: 'Empathy',
  strategy: 'Strategy',
  summary: 'Strategy',
}

function formatDuration(seconds: number): string {
  if (seconds <= 0) return '—'
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

function scoreBar(score: number, colorClass: string) {
  const pct = Math.min(100, Math.max(0, Math.round(score)))
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full', colorClass)} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-14 text-right text-sm font-bold text-gray-900">
        {score.toFixed(1)}/100
      </span>
    </div>
  )
}

function splitLines(text: string | null | undefined): string[] {
  if (!text) return []
  return text.split('\n').map((s) => s.trim()).filter(Boolean)
}

export const SessionDetailPage = () => {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()

  const [session, setSession] = useState<SessionDetail | null>(null)
  const [caseData, setCaseData] = useState<Case | null>(null)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId) return

    const load = async () => {
      try {
        const sessionDetail = await getSession(Number(sessionId))
        setSession(sessionDetail)

        // Fetch case + feedback in parallel; feedback may 404 if not closed yet
        const [caseResult, feedbackResult] = await Promise.allSettled([
          getCase(sessionDetail.caseId),
          sessionDetail.state === 'completed'
            ? fetchFeedback(sessionId)
            : Promise.reject(new Error('not completed')),
        ])

        if (caseResult.status === 'fulfilled') setCaseData(caseResult.value)
        if (feedbackResult.status === 'fulfilled') setFeedback(feedbackResult.value)
      } catch (err: any) {
        console.error('Failed to load session detail:', err)
        setError(err.response?.data?.detail || 'Failed to load session.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [sessionId])

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col">
        <Navbar />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 md:ml-64">
            <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
              <div className="mb-8 space-y-2">
                <div className="h-4 w-64 rounded bg-gray-200 animate-pulse" />
                <div className="h-8 w-80 rounded bg-gray-200 animate-pulse" />
              </div>
              <div className="grid gap-6 lg:grid-cols-3">
                <div className="lg:col-span-2 space-y-3">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <div key={n} className="h-16 rounded-lg bg-gray-100 animate-pulse" />
                  ))}
                </div>
                <div className="h-64 rounded-lg bg-gray-100 animate-pulse" />
              </div>
            </div>
          </main>
        </div>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="flex min-h-screen flex-col">
        <Navbar />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 md:ml-64">
            <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
              <div className="py-20 text-center">
                <p className="mb-4 text-lg text-gray-500">{error || 'Session not found'}</p>
                <Button variant="outline" onClick={() => navigate('/sessions')}>
                  Back to My Sessions
                </Button>
              </div>
            </div>
          </main>
        </div>
      </div>
    )
  }

  const isCompleted = session.state === 'completed'
  const caseTitle = caseData?.title ?? `Case #${session.caseId}`
  const spikesLabel = session.currentSpikesStage
    ? (SPIKES_DISPLAY[session.currentSpikesStage] ?? session.currentSpikesStage)
    : null
  const strengthsList = splitLines(feedback?.strengths).slice(0, 3)
  const improvementsList = splitLines(feedback?.areasForImprovement).slice(0, 3)

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 md:ml-64">
          <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
            {/* Breadcrumb */}
            <nav className="mb-4 flex items-center gap-1 text-sm text-gray-500" aria-label="Breadcrumb">
              <Link
                to="/dashboard"
                className="cursor-pointer hover:text-gray-700 no-underline text-inherit"
              >
                Dashboard
              </Link>
              <ChevronRight className="h-3.5 w-3.5 shrink-0" aria-hidden />
              <Link
                to="/sessions"
                className="cursor-pointer hover:text-gray-700 no-underline text-inherit"
              >
                My Sessions
              </Link>
              <ChevronRight className="h-3.5 w-3.5 shrink-0" aria-hidden />
              <span className="text-gray-900" aria-current="page">
                Session #{session.id}
              </span>
            </nav>

            {/* Header card */}
            <Card className="mb-6">
              <CardContent className="pt-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <h1 className="text-2xl font-bold text-gray-900">{caseTitle}</h1>
                      <span
                        className={cn(
                          'rounded-full px-2.5 py-0.5 text-xs font-medium',
                          isCompleted
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-amber-100 text-amber-700'
                        )}
                      >
                        {isCompleted ? 'Completed' : 'Active'}
                      </span>
                      {spikesLabel && (
                        <span className="rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-700">
                          {spikesLabel}
                        </span>
                      )}
                    </div>

                    <div className="mt-2 flex flex-wrap gap-4 text-sm text-gray-500">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="h-4 w-4" />
                        {formatDate(session.startedAt)}
                      </span>
                      {session.endedAt && (
                        <span className="flex items-center gap-1.5">
                          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                          {formatDate(session.endedAt)}
                        </span>
                      )}
                      <span className="flex items-center gap-1.5">
                        <Timer className="h-4 w-4" />
                        {isCompleted ? formatDuration(session.durationSeconds) : 'In progress'}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Clock className="h-4 w-4" />
                        {session.turns.length} turns
                      </span>
                    </div>
                  </div>

                  <div className="flex gap-2 shrink-0">
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1.5"
                      onClick={() => navigate('/sessions')}
                    >
                      <ArrowLeft className="h-4 w-4" />
                      All Sessions
                    </Button>
                    {isCompleted && feedback ? (
                      <Button
                        size="sm"
                        className="gap-1.5"
                        onClick={() => navigate(`/feedback/${session.id}`)}
                      >
                        Full Feedback
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    ) : !isCompleted ? (
                      <Button
                        size="sm"
                        className="gap-1.5 bg-amber-500 hover:bg-amber-600"
                        onClick={() => navigate(`/case/${session.caseId}`)}
                      >
                        <Play className="h-4 w-4" />
                        Resume Session
                      </Button>
                    ) : null}
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-6 lg:grid-cols-3">
              {/* Transcript */}
              <div className="lg:col-span-2">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Transcript</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {session.turns.length === 0 ? (
                      <p className="py-8 text-center text-sm text-gray-400">
                        No turns recorded for this session.
                      </p>
                    ) : (
                      <div className="space-y-4 max-h-[600px] overflow-y-auto pr-1">
                        {session.turns
                          .slice()
                          .sort((a, b) => a.turnNumber - b.turnNumber)
                          .map((turn) => {
                            const isUser = turn.role === 'user'
                            const spikesTag = turn.spikesStage
                              ? (SPIKES_DISPLAY[turn.spikesStage] ?? turn.spikesStage)
                              : null

                            return (
                              <div
                                key={turn.id}
                                className={cn(
                                  'flex w-full items-start gap-3',
                                  isUser ? 'justify-end' : 'justify-start'
                                )}
                              >
                                {!isUser && (
                                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100">
                                    <Bot className="h-4 w-4 text-emerald-600" />
                                  </div>
                                )}

                                <div className={cn('max-w-[80%]', isUser ? 'items-end' : 'items-start')}>
                                  {spikesTag && (
                                    <div
                                      className={cn(
                                        'mb-1 text-xs font-medium text-purple-600',
                                        isUser ? 'text-right' : 'text-left'
                                      )}
                                    >
                                      {spikesTag}
                                    </div>
                                  )}
                                  <div
                                    className={cn(
                                      'rounded-lg px-4 py-2.5',
                                      isUser
                                        ? 'bg-emerald-600 text-white'
                                        : 'bg-gray-100 text-gray-900'
                                    )}
                                  >
                                    <p className="text-sm whitespace-pre-wrap">{turn.text}</p>
                                    <p
                                      className={cn(
                                        'mt-1 text-xs',
                                        isUser ? 'text-emerald-100' : 'text-gray-500'
                                      )}
                                    >
                                      {new Date(turn.timestamp).toLocaleTimeString()}
                                    </p>
                                  </div>
                                </div>

                                {isUser && (
                                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-200">
                                    <User className="h-4 w-4 text-gray-600" />
                                  </div>
                                )}
                              </div>
                            )
                          })}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Right sidebar: feedback summary or active info */}
              <div className="space-y-4">
                {feedback ? (
                  <>
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base">Scores</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div>
                          <div className="mb-1 flex justify-between text-sm">
                            <span className="text-gray-600">Overall</span>
                          </div>
                          {scoreBar(feedback.overallScore, 'bg-gradient-to-r from-red-400 via-yellow-400 to-emerald-500')}
                        </div>
                        <div>
                          <div className="mb-1 text-sm text-gray-600">Empathy</div>
                          {scoreBar(feedback.empathyScore, 'bg-emerald-500')}
                        </div>
                        <div>
                          <div className="mb-1 text-sm text-gray-600">SPIKES Completion</div>
                          {scoreBar(feedback.spikesCompletionScore, 'bg-purple-500')}
                        </div>

                        <Button
                          variant="ghost"
                          className="mt-2 w-full gap-1.5 bg-transparent border border-[#E5E7EB] text-[#374151] hover:bg-[#F9FAFB] outline-none focus:outline-none focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-offset-0"
                          onClick={() => navigate(`/feedback/${session.id}`)}
                        >
                          View Full Feedback
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </CardContent>
                    </Card>

                    {strengthsList.length > 0 && (
                      <Card>
                        <CardHeader className="pb-3">
                          <CardTitle className="text-base text-emerald-700">Strengths</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <ul className="space-y-2">
                            {strengthsList.map((s, i) => (
                              <li key={i} className="flex items-start gap-2 text-sm">
                                <span className="mt-0.5 text-emerald-500">&#10003;</span>
                                <span>{s}</span>
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    )}

                    {improvementsList.length > 0 && (
                      <Card>
                        <CardHeader className="pb-3">
                          <CardTitle className="text-base text-orange-700">
                            Areas for Improvement
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <ul className="space-y-2">
                            {improvementsList.map((s, i) => (
                              <li key={i} className="flex items-start gap-2 text-sm">
                                <span className="mt-0.5 text-orange-500">&#9679;</span>
                                <span>{s}</span>
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    )}
                  </>
                ) : (
                  <Card>
                    <CardContent className="pt-6">
                      {isCompleted ? (
                        <div className="py-4 text-center text-sm text-gray-500">
                          Feedback is not yet available for this session.
                        </div>
                      ) : (
                        <div className="space-y-3 text-center">
                          <div className="flex h-12 w-12 mx-auto items-center justify-center rounded-full bg-amber-100">
                            <Clock className="h-6 w-6 text-amber-600" />
                          </div>
                          <p className="font-medium text-gray-700">Session in progress</p>
                          <p className="text-sm text-gray-500">
                            Feedback will be available once you end the session.
                          </p>
                          <Button
                            className="mt-2 w-full gap-1.5 bg-amber-500 hover:bg-amber-600"
                            onClick={() => navigate(`/case/${session.caseId}`)}
                          >
                            <Play className="h-4 w-4" />
                            Resume Session
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

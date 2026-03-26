/**
 * Post-session feedback view: scores, SPIKES checklist, and conversation analysis.
 */
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchFeedback } from '@/api/feedback.api'
import type { Feedback as FeedbackType } from '@/api/feedback.api'
import { getSession } from '@/api/sessions.api'
import type { SessionDetail } from '@/types/session'
import { FeedbackChart } from '@/components/FeedbackChart'
import { FeedbackConversationTimeline } from '@/components/FeedbackConversationTimeline'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { formatDateTimeInUserTimeZone } from '@/lib/dateTime'
import { formatPluginName, formatMetricsPluginsDisplay } from '@/lib/formatPluginName'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

/**
 * Canonical SPIKES stage order: `key` matches `turn.spikes_stage`, `label` is UI text.
 */
const SPIKES_STAGE_ORDER: Array<{ key: string; label: string }> = [
  { key: 'setting',    label: 'Setting' },
  { key: 'perception', label: 'Perception' },
  { key: 'invitation', label: 'Invitation' },
  { key: 'knowledge',  label: 'Knowledge' },
  { key: 'emotion',    label: 'Emotion' },
  { key: 'strategy',   label: 'Strategy' },
]

/** Maps legacy letter codes from `spikesCoverage.covered` to canonical stage keys. */
const LETTER_TO_WORD: Record<string, string> = {
  S:  'setting',
  P:  'perception',
  I:  'invitation',
  K:  'knowledge',
  E:  'emotion',
  S2: 'strategy',
  summary: 'strategy',  // alias used in some backend versions
}

/**
 * Normalizes covered stage tokens to lowercase word keys for checklist comparison.
 *
 * @param covered - Raw covered list from feedback
 * @returns Set of canonical keys
 */
function normaliseSpikesCovered(covered: string[]): Set<string> {
  return new Set(
    covered.map((s) => {
      const mapped = LETTER_TO_WORD[s] ?? s.toLowerCase()
      return mapped === 'emotions' ? 'emotion' : mapped
    })
  )
}

function getPreferredStrengths(
  evaluatorMeta: Record<string, unknown> | null | undefined,
  fallbackStrengths: string | null | undefined,
): string[] {
  const llmOutput =
    evaluatorMeta != null &&
    typeof evaluatorMeta === 'object' &&
    'llm_output' in evaluatorMeta
      ? evaluatorMeta.llm_output
      : null

  const llmStrengths =
    llmOutput != null &&
    typeof llmOutput === 'object' &&
    'strengths' in llmOutput
      ? llmOutput.strengths
      : null

  if (Array.isArray(llmStrengths)) {
    const lines = llmStrengths
      .filter((item): item is string => typeof item === 'string')
      .map((item) => item.trim())
      .filter(Boolean)
    if (lines.length > 0) return lines
  }

  return splitLines(fallbackStrengths)
}

function getPreferredImprovements(
  evaluatorMeta: Record<string, unknown> | null | undefined,
  fallbackImprovements: string | null | undefined,
): string[] {
  const llmOutput =
    evaluatorMeta != null &&
    typeof evaluatorMeta === 'object' &&
    'llm_output' in evaluatorMeta
      ? evaluatorMeta.llm_output
      : null

  const llmImprovements =
    llmOutput != null &&
    typeof llmOutput === 'object' &&
    'areas_for_improvement' in llmOutput
      ? llmOutput.areas_for_improvement
      : null

  if (Array.isArray(llmImprovements)) {
    const lines = llmImprovements
      .filter((item): item is string => typeof item === 'string')
      .map((item) => item.trim())
      .filter(Boolean)
    if (lines.length > 0) return lines
  }

  return splitLines(fallbackImprovements)
}

/**
 * Splits multiline feedback text into trimmed non-empty lines.
 *
 * @param text - Raw paragraph text
 * @returns Line array
 */
function splitLines(text: string | null | undefined): string[] {
  if (!text) return []
  return text.split('\n').map((s) => s.trim()).filter(Boolean)
}

/**
 * Clamps a 0–100 score to an integer percentage.
 *
 * @param score - Raw score
 * @returns Rounded percent
 */
function scoreToPercent(score: number): number {
  return Math.min(100, Math.max(0, Math.round(score)))
}

/**
 * Loads feedback + session detail for `sessionId` and renders charts and timeline.
 *
 * @returns Full-page feedback UI or loading/error states
 */
export const Feedback = () => {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [feedback, setFeedback] = useState<FeedbackType | null>(null)
  const [sessionDetail, setSessionDetail] = useState<SessionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    /**
     * Fetches normalized feedback and session turns in parallel.
     */
    const loadFeedback = async () => {
      if (!sessionId) return

      try {
        const [feedbackData, sessionData] = await Promise.all([
          fetchFeedback(sessionId),
          getSession(Number(sessionId)),
        ])
        setFeedback(feedbackData)
        setSessionDetail(sessionData)
      } catch (error: any) {
        console.error('Failed to fetch feedback or session detail:', error)
        setError(
          error?.response?.data?.detail ||
            'Failed to load feedback. The session may not be closed yet.'
        )
      } finally {
        setLoading(false)
      }
    }

    loadFeedback()
  }, [sessionId])

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

  if (error || !feedback) {
    return (
      <div className="flex min-h-screen flex-col">
        <Navbar />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 md:ml-64">
            <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
              <div className="text-center py-16">
                <p className="text-gray-500 text-lg mb-4">
                  {error || 'Feedback not found'}
                </p>
                <Button variant="outline" onClick={() => navigate('/dashboard')}>
                  Back to Dashboard
                </Button>
              </div>
            </div>
          </main>
        </div>
      </div>
    )
  }

  const overallPercent = scoreToPercent(feedback.overallScore)
  const empathyPercent = scoreToPercent(feedback.empathyScore)
  const coveredStages = normaliseSpikesCovered(feedback.spikesCoverage?.covered ?? [])
  const coveragePercent = feedback.spikesCoverage
    ? Math.round(feedback.spikesCoverage.percent * 100)
    : 0
  const strengthsList = getPreferredStrengths(feedback.evaluatorMeta, feedback.strengths)
  const improvementsList = getPreferredImprovements(
    feedback.evaluatorMeta,
    feedback.areasForImprovement,
  )

  return (
    <div className="h-screen flex flex-col">
      <Navbar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 overflow-y-auto md:ml-64">
          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            <nav className="mb-4 text-sm text-gray-500">
              <span className="cursor-pointer hover:text-gray-700" onClick={() => navigate('/dashboard')}>Dashboard</span>
              {' / '}
              <span className="text-gray-900">Feedback Summary</span>
            </nav>

            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900">
                Session Feedback & Analysis
              </h1>
              <p className="mt-2 text-gray-600">
                Comprehensive feedback on your SPIKES communication skills
              </p>
              <div className="mt-4 flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">Overall Score:</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-red-500 via-yellow-500 to-apex-500"
                        style={{ width: `${overallPercent}%` }}
                      />
                    </div>
                    <span className="text-lg font-bold text-gray-900">
                      {feedback.overallScore.toFixed(1)}/100
                    </span>
                  </div>
                </div>
              </div>

              {/* Hero: SPIKES Coverage, Empathy Score, Communication Score */}
              <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
                <div className="bg-purple-50 border-2 border-purple-200 rounded-xl p-6 text-center">
                  <div className="text-sm font-medium text-purple-800 uppercase tracking-wide">SPIKES Coverage</div>
                  <div className="text-4xl font-bold text-purple-600 mt-1">
                    {coveragePercent}<span className="text-xl font-semibold text-purple-500">%</span>
                  </div>
                  <p className="text-xs text-purple-700 mt-1">
                    Session spikes completion
                  </p>
                </div>
                <div className="rounded-xl border-2 border-apex-200 bg-apex-50 p-6 text-center">
                  <div className="text-sm font-medium uppercase tracking-wide text-apex-800">Empathy Score</div>
                  <div className="mt-1 text-4xl font-bold text-apex-600">
                    {feedback.empathyScore.toFixed(1)}<span className="text-xl font-semibold text-apex-500">/100</span>
                  </div>
                  <p className="mt-1 text-xs text-apex-700">Session empathy recognition</p>
                </div>
                <div className="rounded-xl border-2 border-orange-200 bg-orange-50 p-6 text-center">
                  <div className="text-sm font-medium uppercase tracking-wide text-orange-800">Communication Score</div>
                  <div className="mt-1 text-4xl font-bold text-orange-600">
                    {feedback.communicationScore.toFixed(1)}<span className="text-xl font-semibold text-orange-500">/100</span>
                  </div>
                  <p className="mt-1 text-xs text-orange-700">Session communication clarity</p>
                </div>
              </div>
            </div>

            {sessionDetail && (
              <Card className="mb-8 border-slate-200 bg-slate-50/90">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg text-slate-900">Evaluation details</CardTitle>
                  <p className="text-sm font-normal text-slate-600">
                    Plugins recorded for this session (for reproducibility).
                  </p>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-2 text-sm">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Evaluator
                    </div>
                    <div className="mt-1 font-medium text-slate-900">
                      {sessionDetail.evaluatorPlugin
                        ? formatPluginName(sessionDetail.evaluatorPlugin)
                        : 'Server default'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Patient model
                    </div>
                    <div className="mt-1 font-medium text-slate-900">
                      {sessionDetail.patientModelPlugin
                        ? formatPluginName(sessionDetail.patientModelPlugin)
                        : 'Server default'}
                    </div>
                  </div>
                  {formatMetricsPluginsDisplay(sessionDetail.metricsPlugins) ? (
                    <div className="sm:col-span-2">
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Metrics plugins
                      </div>
                      <div className="mt-1 font-medium text-slate-900">
                        {formatMetricsPluginsDisplay(sessionDetail.metricsPlugins)}
                      </div>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            )}

            <div className="space-y-8">
              {/* SPIKES Coverage & Conversation Metrics */}
              <div className="grid gap-6 lg:grid-cols-2">
                <div className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <span className="text-purple-600">📊</span>
                        SPIKES Coverage
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {feedback.spikesCoverage && (
                        <div className="space-y-4">
                          <div className="pt-1 text-sm font-medium text-gray-800">
                            Overall Coverage:{' '}
                            <span className="font-semibold text-purple-700">
                              {feedback.spikesCoverage.coveredCount} / {feedback.spikesCoverage.total}{' '}
                              stages
                            </span>
                            <span className="ml-2 text-gray-500">({coveragePercent}%)</span>
                          </div>

                          <div className="grid grid-cols-2 gap-3">
                            {SPIKES_STAGE_ORDER.map(({ key, label }) => {
                              const covered = coveredStages.has(key)
                              return (
                                <div key={key} className="flex items-center justify-between">
                                  <span className="text-sm font-medium">{label}</span>
                                  <span
                                    className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                                      covered
                                        ? 'bg-apex-100 text-apex-700'
                                        : 'bg-gray-100 text-gray-500'
                                    }`}
                                  >
                                    {covered ? '✓ Covered' : 'Missed'}
                                  </span>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Conversation Metrics</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="rounded-lg bg-apex-50 p-4">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">Empathy Score</span>
                            <span className="text-xl font-bold text-apex-600">
                              {feedback.empathyScore.toFixed(1)}/100
                            </span>
                          </div>
                          <div className="w-full h-4 bg-gray-200 rounded-full mt-2 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-red-500 via-yellow-500 to-apex-500 transition-[width]"
                              style={{ width: `${empathyPercent}%` }}
                            />
                          </div>
                          <p className="text-xs text-gray-500 mt-1">Band: red (low) → yellow → green (high)</p>
                        </div>

                        {feedback.questionBreakdown && (
                          <div className="pt-2">
                            <div className="text-sm font-medium text-gray-800 mb-2">
                              Question Type
                            </div>
                            <div className="grid grid-cols-3 gap-3">
                              <div className="rounded-lg bg-apex-50 p-3 text-center">
                                <div className="text-lg font-bold text-apex-800">
                                  {feedback.questionBreakdown.open}
                                </div>
                                <div className="text-xs text-gray-600">Open</div>
                              </div>
                              <div className="text-center p-3 bg-orange-50 rounded-lg">
                                <div className="text-lg font-bold text-orange-600">
                                  {feedback.questionBreakdown.closed}
                                </div>
                                <div className="text-xs text-gray-600">Closed</div>
                              </div>
                              <div className="text-center p-3 bg-purple-50 rounded-lg">
                                <div className="text-lg font-bold text-purple-600">
                                  {feedback.questionBreakdown.eliciting}
                                </div>
                                <div className="text-xs text-gray-600">Eliciting</div>
                              </div>
                            </div>
                          </div>
                        )}

                        {feedback.linkageStats && (
                          <div className="pt-2 border-t text-sm text-gray-600 space-y-1">
                            <div className="flex justify-between">
                              <span>Empathic Opportunities Detected</span>
                              <span className="font-medium">{feedback.linkageStats.total_eos}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Addressed</span>
                              <span className="font-medium text-apex-600">
                                {feedback.linkageStats.addressed_count} ({Math.round(feedback.linkageStats.addressed_rate * 100)}%)
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Missed</span>
                              <span className="font-medium text-orange-600">
                                {feedback.linkageStats.missed_count} ({Math.round(feedback.linkageStats.missed_rate * 100)}%)
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <div className="space-y-6">
                  {strengthsList.length > 0 && (
                    <Card className="h-80 flex flex-col overflow-hidden border-gray-200">
                      <CardHeader className="flex-none border-b border-apex-100 bg-gradient-to-r from-apex-50 to-white px-5 py-4">
                        <CardTitle className="text-lg text-apex-700">Strengths</CardTitle>
                      </CardHeader>
                      <CardContent className="min-h-0 flex-1 overflow-y-auto px-5 pb-5 pt-5 pr-1">
                        <ul className="space-y-2">
                          {strengthsList.map((strength, index) => (
                            <li key={index} className="flex items-start gap-3 rounded-lg border border-apex-100 bg-apex-50/60 p-2.5">
                              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-apex-100 text-xs font-bold text-apex-700">
                                ✓
                              </span>
                              <span className="text-sm leading-6 text-gray-700">{strength}</span>
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}

                  {improvementsList.length > 0 && (
                    <Card className="h-80 flex flex-col overflow-hidden border-gray-200">
                      <CardHeader className="flex-none border-b border-orange-100 bg-gradient-to-r from-orange-50 to-white px-5 py-4">
                        <CardTitle className="text-lg text-orange-700">Areas for Improvement</CardTitle>
                      </CardHeader>
                      <CardContent className="min-h-0 flex-1 overflow-y-auto px-5 pb-5 pt-5 pr-1">
                        <ul className="space-y-2">
                          {improvementsList.map((area, index) => (
                            <li key={index} className="flex items-start gap-3 rounded-lg border border-orange-100 bg-orange-50/60 p-2.5">
                              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-500" />
                              <span className="text-sm leading-6 text-gray-700">{area}</span>
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </div>

              {/* Conversation Analysis Timeline */}
              {sessionDetail && sessionDetail.turns && sessionDetail.turns.length > 0 ? (
                <FeedbackConversationTimeline turns={sessionDetail.turns} feedback={feedback} />
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>Conversation Analysis</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-500">
                      Conversation analysis unavailable (no transcript data for this session).
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Row 1: Performance Metrics + Session Details */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <FeedbackChart feedback={feedback} />

                <Card className="overflow-hidden border-gray-200">
                  <CardHeader className="border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white px-5 py-4">
                    <CardTitle className="text-lg">Session Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4 px-5 pb-5 pt-5">
                    <div className="grid gap-2.5 sm:grid-cols-2">
                      <div className="rounded-lg border border-gray-100 bg-gray-50/80 p-3">
                        <div className="text-xs font-medium uppercase tracking-wide text-gray-500">Session ID</div>
                        <div className="mt-1 text-sm font-semibold text-gray-900">{feedback.sessionId}</div>
                      </div>
                      <div className="rounded-lg border border-gray-100 bg-gray-50/80 p-3">
                        <div className="text-xs font-medium uppercase tracking-wide text-gray-500">Date</div>
                        <div className="mt-1 text-sm text-gray-900">
                          {formatDateTimeInUserTimeZone(feedback.createdAt)}
                        </div>
                      </div>
                      <div className="rounded-lg border border-emerald-100 bg-emerald-50 p-3">
                        <div className="text-xs font-medium uppercase tracking-wide text-emerald-700">Overall Score</div>
                        <div className="mt-1 text-sm font-bold text-emerald-700">
                          {feedback.overallScore.toFixed(1)}/100
                        </div>
                      </div>
                      {feedback.latencyMsAvg > 0 && (
                        <div className="rounded-lg border border-amber-100 bg-amber-50 p-3">
                          <div className="text-xs font-medium uppercase tracking-wide text-amber-700">
                            Avg Response Latency
                          </div>
                          <div className="mt-1 text-sm font-semibold text-amber-700">
                            {Math.round(feedback.latencyMsAvg)}ms
                          </div>
                        </div>
                      )}
                    </div>
                    {feedback.detailedFeedback && (
                      <div className="rounded-lg border border-gray-100 bg-white p-3 shadow-sm">
                        <span className="text-sm font-medium text-gray-700">Summary</span>
                        <p className="mt-1.5 text-sm leading-6 text-gray-600">{feedback.detailedFeedback}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Row 2: Evaluation Framework (full width) */}
              <Card className="overflow-hidden border-gray-200">
                <CardHeader className="border-b border-gray-100 bg-gradient-to-r from-indigo-50 to-white px-5 py-4">
                  <CardTitle className="text-lg">Evaluation Framework</CardTitle>
                </CardHeader>
                <CardContent className="px-5 pb-5 pt-5">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    <div className="rounded-lg border border-indigo-100 bg-indigo-50/60 p-3">
                      <div className="text-xs font-medium uppercase tracking-wide text-indigo-600">Evaluator</div>
                      <div className="mt-1 text-sm font-semibold text-gray-900">
                        {feedback.evaluatorMeta?.name
                          ? String(feedback.evaluatorMeta.name)
                          : feedback.evaluatorMeta?.evaluator
                            ? String(feedback.evaluatorMeta.evaluator)
                            : 'Apex Hybrid Evaluator'}
                      </div>
                    </div>
                    <div className="rounded-lg border border-indigo-100 bg-indigo-50/60 p-3">
                      <div className="text-xs font-medium uppercase tracking-wide text-indigo-600">Framework</div>
                      <div className="mt-1 text-sm font-semibold text-gray-900">
                        {feedback.evaluatorMeta?.framework
                          ? String(feedback.evaluatorMeta.framework)
                          : 'SPIKES + Clinical Empathy Analysis'}
                      </div>
                    </div>
                    <div className="rounded-lg border border-indigo-100 bg-indigo-50/60 p-3 sm:col-span-2 lg:col-span-1">
                      <div className="text-xs font-medium uppercase tracking-wide text-indigo-600">About</div>
                      <div className="mt-1 text-xs text-gray-500">
                        Scores and feedback were generated by the evaluation plugin configured for this session.
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {feedback.evaluatorMeta != null &&
                Object.keys(feedback.evaluatorMeta).length > 0 && (
                  <Card className="overflow-hidden border-gray-200">
                    <CardHeader className="border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white px-5 py-4">
                      <CardTitle className="text-lg">Evaluator metadata</CardTitle>
                      <p className="text-sm text-gray-500 font-normal mt-1">
                        Scoring pipeline details (phase, merge status, optional LLM fields).
                      </p>
                    </CardHeader>
                    <CardContent className="px-5 pb-5 pt-5">
                      <pre className="max-h-96 overflow-auto text-xs bg-gray-50 border border-gray-100 rounded-lg p-4 text-left whitespace-pre-wrap break-words">
                        {JSON.stringify(feedback.evaluatorMeta, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                )}

              {/* AFCE Breakdown (if data available) */}
              {(feedback.eoCountsByDimension || feedback.responseCountsByType) && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {feedback.eoCountsByDimension && (
                    <Card className="overflow-hidden border-gray-200">
                      <CardHeader className="border-b border-gray-100 bg-gradient-to-r from-apex-50 to-white px-5 py-4">
                        <CardTitle className="text-lg">Empathic Opportunities by Dimension</CardTitle>
                      </CardHeader>
                      <CardContent className="px-5 pb-5 pt-5">
                        <div className="space-y-2.5">
                          {Object.entries(feedback.eoCountsByDimension).map(([dim, counts]) => {
                            const total = counts.explicit + counts.implicit
                            return (
                              <div
                                key={dim}
                                className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50/80 p-3"
                              >
                                <span className="text-sm font-semibold text-gray-900">{dim}</span>
                                <div className="flex items-center gap-3 text-xs">
                                  <span className="rounded-full bg-apex-100 px-2 py-1 font-medium text-apex-800">
                                    {counts.explicit} explicit
                                  </span>
                                  <span className="rounded-full bg-purple-100 px-2 py-1 font-medium text-purple-700">
                                    {counts.implicit} implicit
                                  </span>
                                  <span className="font-semibold text-gray-700">Total {total}</span>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {feedback.responseCountsByType && (
                    <Card className="overflow-hidden border-gray-200">
                      <CardHeader className="border-b border-gray-100 bg-gradient-to-r from-purple-50 to-white px-5 py-4">
                        <CardTitle className="text-lg">Empathic Response Types</CardTitle>
                      </CardHeader>
                      <CardContent className="px-5 pb-5 pt-5">
                        <div className="space-y-2.5">
                          {Object.entries(feedback.responseCountsByType).map(([type, count]) => (
                            <div
                              key={type}
                              className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50/80 p-3"
                            >
                              <span className="text-sm font-semibold capitalize text-gray-900">{type}</span>
                              <span className="rounded-full bg-white px-3 py-1 text-sm font-bold text-gray-700 shadow-sm">
                                {count}
                              </span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}

            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

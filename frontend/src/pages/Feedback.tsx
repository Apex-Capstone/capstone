import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchFeedback } from '@/api/feedback.api'
import type { Feedback as FeedbackType } from '@/api/feedback.api'
import { FeedbackChart } from '@/components/FeedbackChart'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const SPIKES_LABELS: Record<string, string> = {
  S: 'Setting',
  P: 'Perception',
  I: 'Invitation',
  K: 'Knowledge',
  E: 'Empathy',
  S2: 'Strategy',
  setting: 'Setting',
  perception: 'Perception',
  invitation: 'Invitation',
  knowledge: 'Knowledge',
  empathy: 'Empathy',
  strategy: 'Strategy',
  summary: 'Strategy',
}

const ALL_SPIKES_STAGES = ['S', 'P', 'I', 'K', 'E', 'S2']

function splitLines(text: string | null | undefined): string[] {
  if (!text) return []
  return text.split('\n').map((s) => s.trim()).filter(Boolean)
}

function scoreToPercent(score: number): number {
  return Math.round((score / 10) * 100)
}

export const Feedback = () => {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [feedback, setFeedback] = useState<FeedbackType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadFeedback = async () => {
      if (!sessionId) return

      try {
        const data = await fetchFeedback(sessionId)
        setFeedback(data)
      } catch (err: any) {
        console.error('Failed to fetch feedback:', err)
        setError(err.response?.data?.detail || 'Failed to load feedback. The session may not be closed yet.')
      } finally {
        setLoading(false)
      }
    }

    loadFeedback()
  }, [sessionId])

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col">
        <Navbar />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 md:ml-64">
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
  const coveredStages = feedback.spikesCoverage?.covered ?? []
  const coveragePercent = feedback.spikesCoverage
    ? Math.round(feedback.spikesCoverage.percent * 100)
    : 0
  const strengthsList = splitLines(feedback.strengths)
  const improvementsList = splitLines(feedback.areasForImprovement)
  const openRatio = feedback.questionBreakdown
    ? Math.round(feedback.questionBreakdown.ratio_open * 100)
    : null

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 md:ml-64">
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
                        className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 rounded-full"
                        style={{ width: `${overallPercent}%` }}
                      />
                    </div>
                    <span className="text-lg font-bold text-gray-900">
                      {feedback.overallScore.toFixed(1)}/10
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-8">
              {/* SPIKES Coverage & Conversation Metrics */}
              <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>SPIKES Coverage Analysis</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="relative w-48 h-48 mx-auto bg-gray-100 rounded-full flex items-center justify-center">
                        <div className="text-center">
                          <div className="text-2xl font-bold text-purple-600">
                            {coveragePercent}%
                          </div>
                          <div className="text-sm text-gray-600">Coverage</div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        {ALL_SPIKES_STAGES.map((stage) => {
                          const reached = coveredStages.includes(stage)
                          return (
                            <div key={stage} className="flex items-center justify-between">
                              <span className="text-sm font-medium">
                                {SPIKES_LABELS[stage] ?? stage}
                              </span>
                              <span
                                className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                                  reached
                                    ? 'bg-green-100 text-green-700'
                                    : 'bg-gray-100 text-gray-500'
                                }`}
                              >
                                {reached ? 'Reached' : 'Missed'}
                              </span>
                            </div>
                          )
                        })}
                      </div>

                      <div className="text-xs text-gray-500 pt-2 border-t">
                        SPIKES Completion Score: {feedback.spikesCompletionScore.toFixed(1)}/10
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Conversation Metrics</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="bg-emerald-50 p-4 rounded-lg">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">Empathy Score</span>
                          <span className="text-lg font-bold text-emerald-600">
                            {feedback.empathyScore.toFixed(1)}/10
                          </span>
                        </div>
                        <div className="w-full h-2 bg-emerald-200 rounded-full mt-2">
                          <div
                            className="h-full bg-emerald-500 rounded-full"
                            style={{ width: `${empathyPercent}%` }}
                          />
                        </div>
                      </div>

                      {openRatio !== null && (
                        <div className="bg-green-50 p-4 rounded-lg">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">Open Question Ratio</span>
                            <span className="text-lg font-bold text-green-600">
                              {openRatio}%
                            </span>
                          </div>
                          <div className="w-full h-2 bg-green-200 rounded-full mt-2">
                            <div
                              className="h-full bg-green-500 rounded-full"
                              style={{ width: `${openRatio}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {feedback.questionBreakdown && (
                        <div className="grid grid-cols-3 gap-3 pt-2">
                          <div className="text-center p-3 bg-blue-50 rounded-lg">
                            <div className="text-lg font-bold text-blue-600">
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
                      )}

                      {feedback.linkageStats && (
                        <div className="pt-2 border-t text-sm text-gray-600 space-y-1">
                          <div className="flex justify-between">
                            <span>Empathic Opportunities Detected</span>
                            <span className="font-medium">{feedback.linkageStats.total_eos}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Addressed</span>
                            <span className="font-medium text-green-600">
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

              {/* Score chart & Session details */}
              <div className="grid gap-6 lg:grid-cols-2">
                <FeedbackChart feedback={feedback} />

                <Card>
                  <CardHeader>
                    <CardTitle>Session Details</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="font-medium">Session ID:</span>{' '}
                        {feedback.sessionId}
                      </div>
                      <div>
                        <span className="font-medium">Date:</span>{' '}
                        {new Date(feedback.createdAt).toLocaleString()}
                      </div>
                      <div>
                        <span className="font-medium">Overall Score:</span>{' '}
                        <span className="font-bold">{feedback.overallScore.toFixed(1)}/10</span>
                      </div>
                      {feedback.latencyMsAvg > 0 && (
                        <div>
                          <span className="font-medium">Avg Response Latency:</span>{' '}
                          {Math.round(feedback.latencyMsAvg)}ms
                        </div>
                      )}
                    </div>
                    {feedback.detailedFeedback && (
                      <div className="mt-4 pt-4 border-t">
                        <span className="text-sm font-medium text-gray-700">Summary</span>
                        <p className="text-sm text-gray-600 mt-1">{feedback.detailedFeedback}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* AFCE Breakdown (if data available) */}
              {(feedback.eoCountsByDimension || feedback.responseCountsByType) && (
                <div className="grid gap-6 lg:grid-cols-2">
                  {feedback.eoCountsByDimension && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Empathic Opportunities by Dimension</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3">
                          {Object.entries(feedback.eoCountsByDimension).map(([dim, counts]) => {
                            const total = counts.explicit + counts.implicit
                            return (
                              <div key={dim} className="flex items-center justify-between">
                                <span className="text-sm font-medium">{dim}</span>
                                <div className="flex items-center gap-3 text-xs">
                                  <span className="text-blue-600">{counts.explicit} explicit</span>
                                  <span className="text-gray-400">|</span>
                                  <span className="text-purple-600">{counts.implicit} implicit</span>
                                  <span className="font-semibold text-gray-700">= {total}</span>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {feedback.responseCountsByType && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Empathic Response Types</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3">
                          {Object.entries(feedback.responseCountsByType).map(([type, count]) => (
                            <div key={type} className="flex items-center justify-between">
                              <span className="text-sm font-medium capitalize">{type}</span>
                              <span className="text-sm font-bold text-gray-700">{count}</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}

              {/* Strengths & Areas for Improvement */}
              {(strengthsList.length > 0 || improvementsList.length > 0) && (
                <div className="grid gap-6 lg:grid-cols-2">
                  {strengthsList.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-green-700">Strengths</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {strengthsList.map((strength, index) => (
                            <li key={index} className="flex items-start gap-2">
                              <span className="text-green-600 mt-0.5">&#10003;</span>
                              <span className="text-sm">{strength}</span>
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}

                  {improvementsList.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-orange-700">Areas for Improvement</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {improvementsList.map((area, index) => (
                            <li key={index} className="flex items-start gap-2">
                              <span className="text-orange-600 mt-0.5">&#9679;</span>
                              <span className="text-sm">{area}</span>
                            </li>
                          ))}
                        </ul>
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

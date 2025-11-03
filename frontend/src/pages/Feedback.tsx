import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchFeedback } from '@/api/client'
import type { Feedback as FeedbackType } from '@/api/client'
import { FeedbackChart } from '@/components/FeedbackChart'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export const Feedback = () => {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [feedback, setFeedback] = useState<FeedbackType | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadFeedback = async () => {
      if (!sessionId) return

      try {
        const data = await fetchFeedback(sessionId)
        setFeedback(data)
      } catch (error) {
        console.error('Failed to fetch feedback:', error)
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
              {/* TODO: NFR 7.2, 7.3 - Skeleton loader for better UX */}
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

  if (!feedback) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-500">Feedback not found</div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 md:ml-64">
          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            {/* TODO: FR-6, FR-12 - Enhanced breadcrumbs and session info */}
            <nav className="mb-4 text-sm text-gray-500">
              <span>Dashboard</span> / <span className="text-gray-900">Feedback Summary</span>
            </nav>
            
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900">
                Session Feedback & Analysis
              </h1>
              <p className="mt-2 text-gray-600">
                Comprehensive feedback on your SPIKES communication skills • Session ID: {sessionId}
              </p>
              <div className="mt-4 flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">Overall Score:</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 rounded-full"
                        style={{ width: `${feedback.overallScore}%` }}
                      />
                    </div>
                    <span className="text-lg font-bold text-gray-900">{feedback.overallScore}%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* TODO: FR-6, FR-12 - Enhanced feedback layout with SPIKES coverage and metrics */}
            <div className="space-y-8">
              {/* SPIKES Coverage Radar Chart & Key Metrics */}
              <div className="grid gap-6 lg:grid-cols-2">
                {/* SPIKES Coverage Chart Placeholder */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <span className="text-purple-600">📊</span>
                      SPIKES Coverage Analysis
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {feedback.spikesMetrics ? (
                      <div className="space-y-4">
                        {/* Placeholder for radar chart - TODO: Replace with actual chart library */}
                        <div className="relative w-48 h-48 mx-auto bg-gray-100 rounded-full flex items-center justify-center">
                          <div className="text-center">
                            <div className="text-2xl font-bold text-purple-600">
                              {Math.round(Object.values(feedback.spikesMetrics).reduce((a, b) => a + b, 0) / 6)}%
                            </div>
                            <div className="text-sm text-gray-600">Avg Coverage</div>
                          </div>
                        </div>
                        
                        {/* SPIKES stage breakdown */}
                        <div className="grid grid-cols-2 gap-3">
                          {Object.entries(feedback.spikesMetrics).map(([stage, score]) => (
                            <div key={stage} className="flex items-center justify-between">
                              <span className="text-sm font-medium capitalize">{stage}:</span>
                              <div className="flex items-center gap-2">
                                <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                                  <div 
                                    className="h-full bg-purple-500 rounded-full"
                                    style={{ width: `${score}%` }}
                                  />
                                </div>
                                <span className="text-sm font-medium">{score}%</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        SPIKES coverage data not available
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Enhanced Conversation Metrics */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <span className="text-emerald-600">💬</span>
                      Conversation Metrics
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {feedback.conversationMetrics ? (
                      <div className="space-y-4">
                        <div className="grid grid-cols-1 gap-4">
                          <div className="bg-emerald-50 p-4 rounded-lg">
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium">Empathy Score</span>
                              <span className="text-lg font-bold text-emerald-600">
                                {feedback.conversationMetrics.empathyScore}%
                              </span>
                            </div>
                            <div className="w-full h-2 bg-emerald-200 rounded-full mt-2">
                              <div 
                                className="h-full bg-emerald-500 rounded-full"
                                style={{ width: `${feedback.conversationMetrics.empathyScore}%` }}
                              />
                            </div>
                          </div>
                          
                          <div className="bg-green-50 p-4 rounded-lg">
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium">Open Question Ratio</span>
                              <span className="text-lg font-bold text-green-600">
                                {Math.round(feedback.conversationMetrics.openQuestionRatio * 100)}%
                              </span>
                            </div>
                            <div className="w-full h-2 bg-green-200 rounded-full mt-2">
                              <div 
                                className="h-full bg-green-500 rounded-full"
                                style={{ width: `${feedback.conversationMetrics.openQuestionRatio * 100}%` }}
                              />
                            </div>
                          </div>
                          
                          <div className="bg-orange-50 p-4 rounded-lg">
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium">Reassurance Count</span>
                              <span className="text-lg font-bold text-orange-600">
                                {feedback.conversationMetrics.reassuranceCount}
                              </span>
                            </div>
                            <div className="text-xs text-orange-600 mt-1">
                              Times patient was reassured
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        Conversation metrics not available
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Original metrics chart */}
              <div className="grid gap-6 lg:grid-cols-2">
                <FeedbackChart feedback={feedback} />

                <Card>
                  <CardHeader>
                    <CardTitle>Session Details</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="font-medium">Case ID:</span>{' '}
                        {feedback.caseId}
                      </div>
                      <div>
                        <span className="font-medium">Date:</span>{' '}
                        {new Date(feedback.createdAt).toLocaleString()}
                      </div>
                      <div>
                        <span className="font-medium">Overall Score:</span>{' '}
                        <span className="font-bold">{feedback.overallScore}%</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Dialogue Examples */}
              {feedback.dialogueExamples && (
                <div className="grid gap-6 lg:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-green-700">
                        <span>✨</span>
                        Strong Dialogue Examples
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {feedback.dialogueExamples.strong.map((example, index) => (
                          <div key={index} className="bg-green-50 p-4 rounded-lg border-l-4 border-green-500">
                            <blockquote className="text-sm italic mb-2">
                              "{example.text}"
                            </blockquote>
                            <p className="text-xs text-green-700 font-medium">
                              {example.context}
                            </p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-orange-700">
                        <span>💡</span>
                        Areas for Improvement
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {feedback.dialogueExamples.weak.map((example, index) => (
                          <div key={index} className="bg-orange-50 p-4 rounded-lg border-l-4 border-orange-500">
                            <blockquote className="text-sm italic mb-2">
                              "{example.text}"
                            </blockquote>
                            <p className="text-xs text-orange-700 mb-2">
                              <span className="font-medium">Context:</span> {example.context}
                            </p>
                            <p className="text-xs text-orange-800 bg-orange-100 p-2 rounded">
                              <span className="font-medium">Improvement:</span> {example.improvement}
                            </p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Traditional feedback sections */}
              <div className="grid gap-6 lg:grid-cols-3">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-green-700">Strengths</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {feedback.strengths.map((strength, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <span className="text-green-600">✓</span>
                          <span className="text-sm">{strength}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-orange-700">Areas for Improvement</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {feedback.areasForImprovement.map((area, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <span className="text-orange-600">●</span>
                          <span className="text-sm">{area}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-emerald-700">Recommendations</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {feedback.recommendations.map((rec, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <span className="text-emerald-600">→</span>
                          <span className="text-sm">{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}


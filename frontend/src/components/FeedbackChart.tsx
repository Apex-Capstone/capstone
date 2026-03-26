/**
 * Bar-style summary of empathy, SPIKES completion, and overall scores.
 */
import type { Feedback } from '@/api/feedback.api'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'

/** Props for {@link FeedbackChart}. */
interface FeedbackChartProps {
  feedback: Feedback
}

/**
 * Renders three horizontal bars and a footer with the overall score.
 *
 * @param props - {@link FeedbackChartProps}
 * @returns Card with metric bars
 */
export const FeedbackChart = ({ feedback }: FeedbackChartProps) => {
  const metrics = [
    { label: 'Empathy Score', value: feedback.empathyScore, max: 100 },
    { label: 'SPIKES Completion', value: feedback.spikesCompletionScore, max: 100 },
    { label: 'Overall Score', value: feedback.overallScore, max: 100 },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Performance Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {metrics.map((metric) => {
            const percent = Math.min(
              100,
              Math.max(0, Math.round((metric.value / metric.max) * 100)),
            )
            return (
              <div key={metric.label}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700">
                    {metric.label}
                  </span>
                  <span className="text-sm text-gray-600">
                    {metric.value.toFixed(1)}/{metric.max}
                  </span>
                </div>
                <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-apex-600 transition-all rounded-full"
                    style={{ width: `${percent}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
        <div className="mt-6 pt-6 border-t">
          <div className="flex items-center justify-between">
            <span className="text-lg font-semibold">Overall Score</span>
            <span className="text-2xl font-bold text-apex-600">
              {feedback.overallScore.toFixed(1)}/100
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

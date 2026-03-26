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
    {
      label: 'Empathy Score',
      value: feedback.empathyScore,
      max: 100,
      barClassName: 'bg-apex-500',
      accentClassName: 'text-apex-700',
    },
    {
      label: 'SPIKES Completion',
      value: feedback.spikesCompletionScore,
      max: 100,
      barClassName: 'bg-purple-500',
      accentClassName: 'text-purple-700',
    },
    {
      label: 'Overall Score',
      value: feedback.overallScore,
      max: 100,
      barClassName: 'bg-emerald-500',
      accentClassName: 'text-emerald-700',
    },
  ]

  return (
    <Card className="overflow-hidden border-gray-200">
      <CardHeader className="border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white px-5 py-4">
        <CardTitle className="text-lg">Performance Metrics</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 px-5 pb-5 pt-5">
        <div className="space-y-3">
          {metrics.map((metric) => {
            const percent = Math.min(
              100,
              Math.max(0, Math.round((metric.value / metric.max) * 100)),
            )
            return (
              <div key={metric.label} className="rounded-lg border border-gray-100 bg-gray-50/80 p-3">
                <div className="mb-1.5 flex items-center justify-between gap-3">
                  <span className="text-sm font-medium text-gray-700">
                    {metric.label}
                  </span>
                  <span className={`text-sm font-semibold ${metric.accentClassName}`}>
                    {metric.value.toFixed(1)}/{metric.max}
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                  <div
                    className={`h-full rounded-full transition-all ${metric.barClassName}`}
                    style={{ width: `${percent}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
        <div className="rounded-lg border border-emerald-100 bg-emerald-50 px-4 py-4">
          <div className="flex items-center justify-between gap-3">
            <span className="text-base font-semibold text-gray-900">Overall Score</span>
            <span className="text-xl font-bold text-emerald-600">
              {feedback.overallScore.toFixed(1)}/100
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

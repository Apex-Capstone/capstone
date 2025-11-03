import type { Feedback } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'

interface FeedbackChartProps {
  feedback: Feedback
}

export const FeedbackChart = ({ feedback }: FeedbackChartProps) => {
  const metrics = [
    { label: 'Communication', value: feedback.metrics.communication },
    { label: 'Clinical Reasoning', value: feedback.metrics.clinicalReasoning },
    { label: 'Empathy', value: feedback.metrics.empathy },
    { label: 'Professionalism', value: feedback.metrics.professionalism },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Performance Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {metrics.map((metric) => (
            <div key={metric.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">
                  {metric.label}
                </span>
                <span className="text-sm text-gray-600">{metric.value}%</span>
              </div>
              <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-600 transition-all rounded-full"
                  style={{ width: `${metric.value}%` }}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-6 pt-6 border-t">
          <div className="flex items-center justify-between">
            <span className="text-lg font-semibold">Overall Score</span>
            <span className="text-2xl font-bold text-emerald-600">
              {feedback.overallScore}%
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}


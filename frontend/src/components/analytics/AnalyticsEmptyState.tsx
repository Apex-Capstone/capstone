import { Link } from 'react-router-dom'
import { BarChart3 } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

/**
 * Shown when a trainee has no completed sessions yet — encouraging copy + path back to practice.
 */
export function AnalyticsEmptyState() {
  return (
    <Card className="border border-dashed border-gray-200 bg-slate-50/60 shadow-sm">
      <CardContent className="flex flex-col items-center px-6 py-12 text-center sm:px-10 sm:py-14">
        <div
          className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-apex-50 text-apex-600 ring-1 ring-apex-100"
          aria-hidden
        >
          <BarChart3 className="h-7 w-7" strokeWidth={1.75} />
        </div>
        <h2 className="text-lg font-semibold text-gray-900 sm:text-xl">
          Complete a session to see your performance analytics.
        </h2>
        <p className="mt-3 max-w-md text-sm leading-relaxed text-gray-600">
          End a practice session to generate feedback and unlock your empathy score, SPIKES
          coverage, and score trends.
        </p>
        <div className="mt-8 flex flex-col items-stretch gap-3 sm:flex-row sm:justify-center">
          <Link
            to="/dashboard"
            className={cn(buttonVariants({ variant: 'default' }), 'min-w-[200px]')}
          >
            Go to dashboard
          </Link>
          <Link
            to="/sessions"
            className={cn(buttonVariants({ variant: 'outline' }), 'min-w-[200px]')}
          >
            View sessions
          </Link>
        </div>
        <p className="mt-6 text-xs text-gray-500">
          Tip: finish a case and close the session so it counts toward your analytics.
        </p>
      </CardContent>
    </Card>
  )
}

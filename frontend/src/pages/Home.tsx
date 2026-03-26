/**
 * Marketing landing for the APEX research platform; redirects authenticated users to the dashboard.
 */
import { Link, Navigate } from 'react-router-dom'
import { useAuthGate } from '@/hooks/useAuthGate'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MessageSquare, BarChart3, Puzzle, ArrowRight, Microscope } from 'lucide-react'

/** Static hero visual: conversation + evaluation cues (no live data). */
function HeroConversationMock() {
  return (
    <div
      className="relative mx-auto w-full max-w-lg lg:max-w-none rounded-2xl border border-gray-200/80 bg-white shadow-[0_24px_60px_-12px_rgba(15,23,42,0.12)] ring-1 ring-gray-950/5"
      aria-hidden
    >
      <div className="flex items-center gap-2 rounded-t-2xl border-b border-gray-100 bg-gray-50/90 px-4 py-3">
        <span className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-gray-300" />
          <span className="h-2.5 w-2.5 rounded-full bg-gray-200" />
          <span className="h-2.5 w-2.5 rounded-full bg-gray-200" />
        </span>
        <span className="flex-1 truncate px-2 text-center text-xs font-medium text-gray-500">
          Session · Simulated encounter
        </span>
      </div>
      <div className="space-y-4 p-5 sm:p-6">
        <div className="flex justify-start">
          <div className="max-w-[88%] rounded-2xl rounded-tl-md bg-gray-100 px-4 py-3 text-sm leading-relaxed text-gray-800">
            I&apos;m worried about what the scan might show. Can you walk me through what happens next?
          </div>
        </div>
        <div className="flex justify-end">
          <div className="max-w-[88%] rounded-2xl rounded-tr-md border border-emerald-800/10 bg-emerald-700/10 px-4 py-3 text-sm leading-relaxed text-gray-900">
            I understand this is unsettling. I&apos;ll explain the results in plain language, then we&apos;ll
            discuss options together.
          </div>
        </div>
        <div className="space-y-3 rounded-xl border border-gray-100 bg-gray-50/80 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">
            Structured feedback preview
          </p>
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3 text-xs">
              <span className="text-gray-600">SPIKES alignment</span>
              <span className="font-medium tabular-nums text-gray-900">High</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
              <div className="h-full w-[82%] rounded-full bg-emerald-700" />
            </div>
            <div className="flex items-center justify-between gap-3 pt-1 text-xs">
              <span className="text-gray-600">Empathic opportunity</span>
              <span className="font-medium text-gray-900">Addressed</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export const Home = () => {
  const gate = useAuthGate()

  if (gate === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center text-gray-500">
        Loading...
      </div>
    )
  }

  if (gate === 'authed') {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-emerald-50">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Hero */}
        <section className="mb-20 lg:mb-28">
          <div className="grid items-center gap-14 lg:grid-cols-2 lg:gap-16 xl:gap-20">
            <div className="order-2 text-center lg:order-1 lg:text-left">
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white/90 px-3 py-1.5 text-xs font-medium text-gray-600 shadow-sm">
                <Microscope className="h-3.5 w-3.5 text-emerald-700" aria-hidden />
                APEX
              </div>
              <h1 className="text-balance text-4xl font-bold tracking-tight text-gray-950 sm:text-5xl lg:text-[2.65rem] lg:leading-[1.08] xl:text-5xl">
                Clinical communication research with AI-simulated patients
              </h1>
              <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-gray-600 lg:mx-0">
                Produce comparable sessions, quantified communication outcomes, and analysis-ready exports—so
                studies stay controlled from protocol to dataset.
              </p>
              <ul
                className="mt-8 flex flex-wrap justify-center gap-2.5 lg:justify-start"
                aria-label="Platform characteristics"
              >
                <li className="rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-800 shadow-sm">
                  Framework-aligned scoring
                </li>
                <li className="rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-800 shadow-sm">
                  Reproducible experimental conditions
                </li>
                <li className="rounded-md border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-800 shadow-sm">
                  Structured research export
                </li>
              </ul>
              <div className="mt-10">
                <Link to="/login">
                  <Button
                    size="lg"
                    className="h-12 rounded-lg bg-gray-950 px-8 text-base font-semibold text-white shadow-md hover:bg-gray-900"
                  >
                    Sign in
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
              </div>
            </div>
            <div className="order-1 flex justify-center lg:order-2 lg:justify-end">
              <div className="w-full max-w-md lg:max-w-lg">
                <HeroConversationMock />
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <div className="grid gap-8 md:grid-cols-3 mb-16">
          <Card>
            <CardHeader>
              <div className="rounded-lg bg-emerald-100 w-12 h-12 flex items-center justify-center mb-4">
                <MessageSquare className="h-6 w-6 text-emerald-600" />
              </div>
              <CardTitle>Simulated clinical dialogue</CardTitle>
              <CardDescription>
                Run doctor–patient conversations with AI-simulated patients and configurable virtual cases.
                Plug in different patient simulation models to compare how clinicians communicate in sensitive
                interactions.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <div className="rounded-lg bg-emerald-100 w-12 h-12 flex items-center justify-center mb-4">
                <BarChart3 className="h-6 w-6 text-emerald-600" />
              </div>
              <CardTitle>Framework-aligned evaluation</CardTitle>
              <CardDescription>
                Automatically score turns and sessions using communication frameworks such as SPIKES and
                empathy-oriented metrics aligned with the Appraisal Framework for Clinical Empathy (AFCE).
                Swap and compare evaluation approaches as your study design evolves.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <div className="rounded-lg bg-purple-100 w-12 h-12 flex items-center justify-center mb-4">
                <Puzzle className="h-6 w-6 text-purple-600" />
              </div>
              <CardTitle>Modular research stack</CardTitle>
              <CardDescription>
                Extend the platform with plug-in patient models, evaluators, and metrics providers. Collect
                structured conversation analytics and export data for research—so teams can test hypotheses
                about clinical empathy and communication rigorously.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>

        {/* CTA Section */}
        <div className="text-center">
          <Card className="bg-emerald-600 text-white border-0">
            <CardHeader>
              <CardTitle className="text-2xl mb-2">Access the platform</CardTitle>
              <CardDescription className="text-emerald-100">
                Sign in to run or review sessions, explore feedback and analytics, and use research exports
                where your role allows.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link to="/login">
                <Button size="lg" variant="secondary" className="w-full sm:w-auto">
                  Sign in to your account
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

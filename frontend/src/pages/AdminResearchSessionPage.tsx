/**
 * Admin view for a single anonymized research session (read-only detail from research API).
 */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchResearchSessionByAnonId } from '@/api/research.api'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowLeft } from 'lucide-react'

export const AdminResearchSessionPage = () => {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!sessionId) {
      setError('Missing session id')
      setLoading(false)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const data = await fetchResearchSessionByAnonId(sessionId)
        if (!cancelled) setDetail(data)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load session')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [sessionId])

  return (
    <div className="h-screen flex flex-col">
      <Navbar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 overflow-y-auto md:ml-64">
          <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
            <div className="mb-6">
              <Link
                to="/research/sessions"
                className="inline-flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Research Sessions
              </Link>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Research session</h1>
            <p className="mt-1 font-mono text-sm text-gray-600 break-all">{sessionId}</p>

            {loading && <p className="mt-6 text-gray-500">Loading…</p>}
            {error && <p className="mt-6 text-red-600">{error}</p>}
            {!loading && !error && detail && (
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle className="text-base">Session payload</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="max-h-[480px] overflow-auto rounded-md bg-gray-50 p-4 text-xs text-gray-800">
                    {JSON.stringify(detail, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { listCases } from '@/api/cases.api'
import { createSession } from '@/api/sessions.api'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { CaseCard } from '@/components/CaseCard'
import { Button } from '@/components/ui/button'
import type { Case } from '@/types/case'

export const Cases = () => {
  const navigate = useNavigate()
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)
  const [creatingSessionForCase, setCreatingSessionForCase] = useState<number | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await listCases()
        setCases(res.items ?? [])
      } catch (err) {
        console.error('Failed to fetch cases:', err)
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  const handleStartNewSession = async (caseId: number) => {
    if (creatingSessionForCase) return
    setCreatingSessionForCase(caseId)
    try {
      const session = await createSession(caseId, { forceNew: true })
      navigate(`/case/${caseId}?sessionId=${session.id}`)
    } catch (error) {
      console.error('Failed to start a new session:', error)
      toast.error('Failed to start session. Please try again.')
    } finally {
      setCreatingSessionForCase(null)
    }
  }

  return (
    <div className="h-screen flex flex-col">
      <Navbar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 min-h-0 overflow-y-auto md:ml-64">
          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            <nav className="mb-4 text-sm text-gray-500">
              <span className="cursor-pointer hover:text-gray-700" onClick={() => navigate('/dashboard')}>
                Dashboard
              </span>
              {' / '}
              <span className="text-gray-900">Cases</span>
            </nav>

            <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Patient Cases</h1>
                <p className="mt-2 text-gray-600">
                  Select a case to start a new practice session.
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={() => navigate('/sessions')}>
                View my sessions
              </Button>
            </div>

            {loading ? (
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {[1, 2, 3, 4, 5, 6].map((n) => (
                  <div key={n} className="bg-white border rounded-lg p-6 animate-pulse">
                    <div className="flex justify-between items-start mb-4">
                      <div className="h-5 w-32 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded" />
                      <div className="h-5 w-14 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded-full" />
                    </div>
                    <div className="space-y-2 mb-4">
                      <div className="h-4 w-full bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded" />
                      <div className="h-4 w-3/4 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded" />
                    </div>
                    <div className="flex justify-between items-center">
                      <div className="h-3 w-24 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded" />
                      <div className="h-3 w-20 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded" />
                    </div>
                  </div>
                ))}
              </div>
            ) : cases.length === 0 ? (
              <div className="rounded-lg border border-gray-200 bg-white p-12 text-center">
                <p className="text-gray-500">
                  No patient cases available. Contact your administrator.
                </p>
              </div>
            ) : (
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {cases.map((caseItem) => (
                  <CaseCard
                    key={caseItem.id}
                    caseData={caseItem as any}
                    onClick={handleStartNewSession}
                    selected={creatingSessionForCase === caseItem.id}
                  />
                ))}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}


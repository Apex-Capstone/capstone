import { useEffect, useState } from 'react'
import { listCases } from '@/api/cases.api'
import type { Case } from '@/types/case'          // <-- fix import
import { CaseCard } from '@/components/CaseCard'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { useAuthStore } from '@/store/authStore'

export const Dashboard = () => {
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)
  const { user } = useAuthStore()

  useEffect(() => {
    const loadCases = async () => {
      try {
        const { items } = await listCases()
        setCases(items)
      } catch (error) {
        console.error('Failed to fetch cases:', error)
      } finally {
        setLoading(false)
      }
    }
    loadCases()
  }, [])

  // derive soft status counts (since BE Case has no status)
  const statusCounts = cases.reduce(
    (acc, c) => {
      const s = (c as any)?.status ?? 'pending'
      acc[s] = (acc[s] || 0) + 1
      return acc
    },
    {} as Record<'completed' | 'in_progress' | 'pending' | string, number>
  )

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 md:ml-64">
          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            <nav className="mb-4 text-sm text-gray-500">Dashboard</nav>

            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900">
                Welcome back, {user?.name || (user as any)?.full_name || user?.email}
              </h1>
              <p className="mt-2 text-gray-600">
                Practice delivering difficult news using the SPIKES communication framework
              </p>
              <div className="mt-4 flex items-center gap-4 text-sm">
                <span className="font-medium text-gray-700">Role:</span>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-800 font-medium">
                  {user?.role}
                </span>
                {user?.role === 'admin' && (
                  <span className="text-gray-500">• You have access to admin features</span>
                )}
              </div>
            </div>

            {loading ? (
              <div>
                <div className="mb-6">
                  <div className="h-6 w-48 bg-gray-200 rounded animate-pulse mb-2" />
                  <div className="h-4 w-64 bg-gray-200 rounded animate-pulse" />
                </div>
                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                  {[1,2,3,4,5,6].map((n) => (
                    <div key={n} className="bg-white border rounded-lg p-6 animate-pulse">
                      <div className="flex justify-between items-start mb-4">
                        <div className="h-5 w-32 bg-gray-200 rounded" />
                        <div className="h-6 w-20 bg-gray-200 rounded-full" />
                      </div>
                      <div className="space-y-2 mb-4">
                        <div className="h-4 w-full bg-gray-200 rounded" />
                        <div className="h-4 w-3/4 bg-gray-200 rounded" />
                      </div>
                      <div className="flex justify-between items-center">
                        <div className="h-3 w-24 bg-gray-200 rounded" />
                        <div className="h-3 w-20 bg-gray-200 rounded" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : cases.length === 0 ? (
              <div className="rounded-lg border border-gray-200 bg-white p-12 text-center">
                <p className="text-gray-500">No virtual patient cases available. Contact your administrator.</p>
              </div>
            ) : (
              <div>
                <div className="mb-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">Virtual Patient Cases</h2>
                  <p className="text-gray-600">
                    Select a case to practice your communication skills using the SPIKES framework
                  </p>
                </div>

                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                  {cases.map((caseItem) => (
                    <CaseCard key={caseItem.id} caseData={caseItem as any} />
                  ))}
                </div>

                {/* Quick stats (tolerant if status doesn't exist) */}
                <div className="mt-12 grid gap-4 sm:grid-cols-3">
                  <div className="bg-white rounded-lg border p-4 text-center">
                    <div className="text-2xl font-bold text-emerald-600">
                      {statusCounts['completed'] ?? 0}
                    </div>
                    <div className="text-sm text-gray-600">Completed Cases</div>
                  </div>
                  <div className="bg-white rounded-lg border p-4 text-center">
                    <div className="text-2xl font-bold text-orange-600">
                      {statusCounts['in_progress'] ?? 0}
                    </div>
                    <div className="text-sm text-gray-600">In Progress</div>
                  </div>
                  <div className="bg-white rounded-lg border p-4 text-center">
                    <div className="text-2xl font-bold text-gray-600">
                      {statusCounts['pending'] ?? cases.length}
                    </div>
                    <div className="text-sm text-gray-600">Available</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { fetchAdminStats } from '@/api/client'
import type { AdminStats } from '@/api/client'
import { MetricCard } from '@/components/MetricCard'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Button } from '@/components/ui/button'
import { Users, FileText, Activity, TrendingUp, Download, Plus, Settings, BarChart3, MessageSquare } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export const Admin = () => {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'sessions' | 'analytics' | 'cases'>('overview')

  useEffect(() => {
    const loadStats = async () => {
      try {
        const data = await fetchAdminStats()
        setStats(data)
      } catch (error) {
        console.error('Failed to fetch admin stats:', error)
      } finally {
        setLoading(false)
      }
    }

    loadStats()
  }, [])

  // TODO: FR-7, FR-13, FR-14 - Admin functionality handlers
  const handleExportData = () => {
    const dataToExport = {
      stats,
      exportedAt: new Date().toISOString(),
      type: 'admin_analytics'
    }
    const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `medllm_analytics_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleCreateCase = () => {
    // TODO: Implement case creation when backend is ready
    alert('Case creation will be implemented when backend API is ready')
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'users', label: 'User Management', icon: Users },
    { id: 'sessions', label: 'Session Logs', icon: MessageSquare },
    { id: 'analytics', label: 'Analytics', icon: TrendingUp },
    { id: 'cases', label: 'Case Management', icon: FileText },
  ] as const

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-500">Loading admin dashboard...</div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-500">Failed to load stats</div>
      </div>
    )
  }

  const renderTabContent = () => {
    if (!stats) return null

    switch (activeTab) {
      case 'overview':
        return (
          <div className="space-y-8">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                title="Total Users"
                value={stats.totalUsers}
                icon={Users}
                description="Registered trainees"
              />
              <MetricCard
                title="Total Cases"
                value={stats.totalCases}
                icon={FileText}
                description="Available training cases"
              />
              <MetricCard
                title="Active Sessions"
                value={stats.activeSessions}
                icon={Activity}
                description="Currently in progress"
              />
              <MetricCard
                title="Average Score"
                value={`${stats.averageScore}%`}
                icon={TrendingUp}
                description="Across all sessions"
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {stats.recentActivity.map((activity, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between border-b pb-3 last:border-0 last:pb-0"
                    >
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {activity.action}
                        </p>
                        <p className="text-xs text-gray-500">
                          User: {activity.userId}
                        </p>
                      </div>
                      <p className="text-xs text-gray-500">
                        {new Date(activity.timestamp).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )

      case 'users':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>User Overview</CardTitle>
              </CardHeader>
              <CardContent>
                {stats.userOverview ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-2">Name</th>
                          <th className="text-left py-2">Email</th>
                          <th className="text-left py-2">Role</th>
                          <th className="text-left py-2">Avg Score</th>
                          <th className="text-left py-2">Cases Completed</th>
                          <th className="text-left py-2">Last Active</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stats.userOverview.map((user) => (
                          <tr key={user.id} className="border-b">
                            <td className="py-2">{user.name}</td>
                            <td className="py-2">{user.email}</td>
                            <td className="py-2">
                              <span className={cn(
                                'px-2 py-1 rounded-full text-xs font-medium',
                                user.role === 'admin' 
                                  ? 'bg-purple-100 text-purple-800' 
                                  : 'bg-emerald-100 text-emerald-800'
                              )}>
                                {user.role}
                              </span>
                            </td>
                            <td className="py-2">{user.averageScore.toFixed(1)}%</td>
                            <td className="py-2">{user.completedCases}</td>
                            <td className="py-2">{new Date(user.lastActive).toLocaleDateString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-gray-500">User overview data not available</p>
                )}
              </CardContent>
            </Card>
          </div>
        )

      case 'sessions':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Session Logs</CardTitle>
              </CardHeader>
              <CardContent>
                {stats.sessionLogs ? (
                  <div className="space-y-4">
                    {stats.sessionLogs.map((session) => (
                      <div key={session.id} className="bg-gray-50 p-4 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-medium">Session {session.id}</div>
                          <div className="text-sm text-gray-500">
                            {session.score && <span className="font-medium">Score: {session.score}%</span>}
                          </div>
                        </div>
                        <div className="text-sm text-gray-600 grid grid-cols-2 gap-4">
                          <div>User: {session.userId}</div>
                          <div>Case: {session.caseId}</div>
                          <div>Start: {new Date(session.startTime).toLocaleString()}</div>
                          <div>End: {session.endTime ? new Date(session.endTime).toLocaleString() : 'In progress'}</div>
                        </div>
                        {session.transcript && (
                          <div className="mt-2 p-2 bg-white rounded border text-xs">
                            <strong>Transcript Preview:</strong> {session.transcript.substring(0, 100)}...
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500">Session logs not available</p>
                )}
              </CardContent>
            </Card>
          </div>
        )

      case 'analytics':
        return (
          <div className="space-y-6">
            {stats.analyticsData && (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle>Performance Trends</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div>
                        <h4 className="font-medium mb-2">Average Score by Month</h4>
                        <div className="space-y-2">
                          {stats.analyticsData.averageScoreByMonth.map((data, index) => (
                            <div key={index} className="flex items-center justify-between">
                              <span className="text-sm">{data.month}</span>
                              <div className="flex items-center gap-2">
                                <div className="w-20 h-2 bg-gray-200 rounded-full">
                                  <div 
                                    className="h-full bg-emerald-500 rounded-full"
                                    style={{ width: `${data.score}%` }}
                                  />
                                </div>
                                <span className="text-sm font-medium">{data.score}%</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <div className="grid gap-6 lg:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle>Completion Rates by Difficulty</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {stats.analyticsData.completionRates.map((data, index) => (
                          <div key={index} className="flex items-center justify-between">
                            <span className="text-sm capitalize">{data.difficulty}</span>
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-2 bg-gray-200 rounded-full">
                                <div 
                                  className="h-full bg-green-500 rounded-full"
                                  style={{ width: `${data.rate * 100}%` }}
                                />
                              </div>
                              <span className="text-sm font-medium">{Math.round(data.rate * 100)}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Common Challenges</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {stats.analyticsData.commonChallenges.map((challenge, index) => (
                          <div key={index} className="flex items-center justify-between text-sm">
                            <span>{challenge.challenge}</span>
                            <span className="font-medium">{challenge.frequency} instances</span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </>
            )}
          </div>
        )

      case 'cases':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium">Case Management</h3>
              <Button onClick={handleCreateCase} className="flex items-center gap-2">
                <Plus className="h-4 w-4" />
                Create New Case
              </Button>
            </div>
            
            <Card>
              <CardHeader>
                <CardTitle>Case Management (Placeholder)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <Settings className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500 mb-4">
                    Case management functionality will be implemented when backend API is ready.
                  </p>
                  <div className="space-y-2 text-sm text-gray-600">
                    <p>• Create and edit virtual patient cases</p>
                    <p>• Configure SPIKES scenarios</p>
                    <p>• Set difficulty levels and patient demographics</p>
                    <p>• Manage case assignments</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 md:ml-64">
          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            {/* TODO: FR-7, FR-13, FR-14 - Enhanced admin dashboard with tabs */}
            <nav className="mb-4 text-sm text-gray-500">
              Dashboard / <span className="text-gray-900">Admin</span>
            </nav>
            
            <div className="mb-8">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-gray-900">
                    Admin Dashboard
                  </h1>
                  <p className="mt-2 text-gray-600">
                    Manage users, monitor sessions, and analyze platform performance
                  </p>
                </div>
                <Button 
                  onClick={handleExportData}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <Download className="h-4 w-4" />
                  Export JSON
                </Button>
              </div>
            </div>

            {/* Tab Navigation */}
            <div className="border-b border-gray-200 mb-8">
              <nav className="flex gap-8">
                {tabs.map((tab) => {
                  const Icon = tab.icon
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={cn(
                        'flex items-center gap-2 py-2 px-4 rounded-md font-medium text-sm transition-colors',
                        activeTab === tab.id
                          ? 'bg-emerald-600 text-white shadow-sm'
                          : 'bg-gray-100 text-gray-700 hover:bg-emerald-100 hover:text-emerald-700 border border-gray-200'
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {tab.label}
                    </button>
                  )
                })}
              </nav>
            </div>

            {/* Tab Content */}
            {renderTabContent()}
          </div>
        </main>
      </div>
    </div>
  )
}


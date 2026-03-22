import { useEffect, useState } from 'react'
import {
  fetchAdminStats,
  fetchAdminSessions,
  fetchAdminSessionDetail,
  fetchAdminPluginRegistry,
  type AdminStats,
  type AdminSessionListResponse,
  type AdminSessionDetailResponse,
} from '@/api/admin.api'
import type { PluginsResponse } from '@/types/plugins'
import { MetricCard } from '@/components/MetricCard'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Button } from '@/components/ui/button'
import { Users, FileText, Activity, TrendingUp, Download, Plus, BarChart3, MessageSquare, Puzzle, ExternalLink, Clock, UserCheck } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

// ---- Session detail panel ----
function SessionDetailPanel({
  detail,
  onClose,
}: {
  detail: AdminSessionDetailResponse
  onClose: () => void
}) {
  const { session, feedback, metrics_timeline } = detail
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Session {session.id} – Transcript & Feedback</CardTitle>
        <Button variant="outline" size="sm" onClick={onClose}>
          Close
        </Button>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Transcript */}
        <section>
          <h4 className="font-medium mb-3">Transcript</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto border rounded-lg p-3 bg-gray-50">
            {session.turns.length === 0 ? (
              <p className="text-gray-500 text-sm">No turns</p>
            ) : (
              session.turns.map((t) => (
                <div key={t.id} className="text-sm">
                  <span className="font-medium text-gray-700">
                    Turn {t.turn_number} ({t.role})
                  </span>
                  <span className="text-gray-500 ml-2 text-xs">
                    {new Date(t.timestamp).toLocaleString()}
                  </span>
                  <p className="mt-1 text-gray-900">{t.text}</p>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Feedback summary */}
        <section>
          <h4 className="font-medium mb-3">Feedback Summary</h4>
          {feedback ? (
            <div className="space-y-2 border rounded-lg p-3 bg-gray-50">
              <div>
                <span className="text-sm font-medium">Empathy score: </span>
                <span>{feedback.empathy_score.toFixed(1)}</span>
              </div>
              <div>
                <span className="text-sm font-medium">Overall score: </span>
                <span>{feedback.overall_score.toFixed(1)}</span>
              </div>
              {feedback.strengths && (
                <div>
                  <span className="text-sm font-medium">Strengths: </span>
                  <p className="text-sm text-gray-700 mt-1">{feedback.strengths}</p>
                </div>
              )}
              {feedback.areas_for_improvement && (
                <div>
                  <span className="text-sm font-medium">Areas for improvement: </span>
                  <p className="text-sm text-gray-700 mt-1">{feedback.areas_for_improvement}</p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No feedback generated yet.</p>
          )}
        </section>

        {/* Metrics timeline */}
        <section>
          <h4 className="font-medium mb-3">Metrics Timeline</h4>
          {metrics_timeline.length === 0 ? (
            <p className="text-gray-500 text-sm">No metrics timeline</p>
          ) : (
            <ul className="space-y-2 border rounded-lg p-3 bg-gray-50 max-h-48 overflow-y-auto">
              {metrics_timeline.map((m, i) => (
                <li key={i} className="text-sm flex justify-between gap-4">
                  <span>Turn {m.turn_number}</span>
                  <span>{new Date(m.timestamp).toLocaleString()}</span>
                  <span>Empathy: {m.empathy_score.toFixed(1)}</span>
                  <span>{m.question_type}</span>
                  <span>{m.spikes_stage}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </CardContent>
    </Card>
  )
}

// ---- NEW: cases CRUD imports ----
import { CasesTable } from '@/components/admin/CasesTable'
import { CaseForm } from '@/components/admin/CaseForm'
import { listCases, createCase, updateCase, deleteCase } from '@/api/cases.api'
import type { Case } from '@/types/case'

export const Admin = () => {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'sessions' | 'analytics' | 'cases' | 'plugins'>('overview')

  // ---- NEW: cases state ----
  const [caseItems, setCaseItems] = useState<Case[]>([])
  const [caseLoading, setCaseLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create')
  const [editing, setEditing] = useState<Case | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // ---- Session logs state ----
  const [sessionsData, setSessionsData] = useState<AdminSessionListResponse | null>(null)
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [sessionsError, setSessionsError] = useState<string | null>(null)
  const [selectedDetail, setSelectedDetail] = useState<AdminSessionDetailResponse | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)

  // Plugins page: installed plugins (name + version)
  const [installedPlugins, setInstalledPlugins] = useState<PluginsResponse | null>(null)
  const [pluginsLoading, setPluginsLoading] = useState(false)
  const [pluginsError, setPluginsError] = useState<string | null>(null)

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

  // ---- NEW: fetch cases when switching to the Cases tab ----
  const refreshCases = async () => {
    setCaseLoading(true)
    try {
      const { items } = await listCases()
      setCaseItems(items)
    } catch (e) {
      console.error('Failed to fetch cases:', e)
    } finally {
      setCaseLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'cases') {
      void refreshCases()
    }
  }, [activeTab])

  const refreshSessions = async () => {
    setSessionsLoading(true)
    setSessionsError(null)
    try {
      const data = await fetchAdminSessions(0, 50)
      setSessionsData(data)
    } catch (e) {
      console.error('Failed to fetch sessions:', e)
      setSessionsError('Failed to load session logs')
    } finally {
      setSessionsLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'sessions') {
      void refreshSessions()
    }
  }, [activeTab])

  const loadPlugins = async () => {
    setPluginsLoading(true)
    setPluginsError(null)
    try {
      const data = await fetchAdminPluginRegistry()
      setInstalledPlugins(data)
    } catch (e) {
      console.error('Failed to fetch plugins:', e)
      setPluginsError('Failed to load plugins')
    } finally {
      setPluginsLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'plugins') {
      void loadPlugins()
    }
  }, [activeTab])

  const handleSessionRowClick = async (sessionId: number) => {
    setSelectedDetail(null)
    setDetailError(null)
    setDetailLoading(true)
    try {
      const detail = await fetchAdminSessionDetail(String(sessionId))
      setSelectedDetail(detail)
    } catch (e) {
      console.error('Failed to fetch session detail:', e)
      setDetailError('Failed to load session detail')
    } finally {
      setDetailLoading(false)
    }
  }

  const clearSelectedSession = () => {
    setSelectedDetail(null)
    setDetailError(null)
  }

  const handleExportData = () => {
    const dataToExport = {
      stats,
      exportedAt: new Date().toISOString(),
      type: 'admin_analytics',
    }
    const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `apex_analytics_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'users', label: 'User Management', icon: Users },
    { id: 'sessions', label: 'Session Logs', icon: MessageSquare },
    { id: 'analytics', label: 'Analytics', icon: TrendingUp },
    { id: 'cases', label: 'Case Management', icon: FileText },
    { id: 'plugins', label: 'Plugins', icon: Puzzle },
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

  // ---- NEW: cases handlers ----
  const onCreateClick = () => {
    setEditing(null)
    setFormMode('create')
    setFormOpen(true)
  }

  const onEdit = (c: Case) => {
    setEditing(c)
    setFormMode('edit')
    setFormOpen(true)
  }

  const onDelete = async (id: number) => {
    if (!confirm('Delete this case?')) return
    await deleteCase(id)
    await refreshCases()
  }

  const onSubmitForm = async (vals: Partial<Case>) => {
    setSubmitting(true)
    try {
      if (formMode === 'create') {
        await createCase(vals)
      } else if (editing) {
        await updateCase(editing.id, vals)
      }
      setFormOpen(false)
      await refreshCases()
    } finally {
      setSubmitting(false)
    }
  }

  const renderTabContent = () => {
    if (!stats) return null

    switch (activeTab) {
      case 'overview':
        return (
          <div className="space-y-8">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard title="Total Users" value={stats.totalUsers} icon={Users} description="Registered trainees" />
              <MetricCard title="Total Cases" value={stats.totalCases} icon={FileText} description="Available training cases" />
              <MetricCard title="Active Sessions" value={stats.activeSessions} icon={Activity} description="Currently in progress" />
              <MetricCard title="Average Score" value={`${(Number.parseFloat(stats.averageScore.toString())).toFixed(2)}%`} icon={TrendingUp} description="Across all sessions" />
            </div>

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                title="Completed Sessions"
                value={stats.completedSessions ?? '—'}
                icon={BarChart3}
                description="Sessions marked completed"
              />
              <MetricCard
                title="Total Sessions"
                value={stats.totalSessions ?? '—'}
                icon={MessageSquare}
                description="All sessions in the system"
              />
              <MetricCard
                title="Active users (30d)"
                value={stats.activeUsersLast30Days ?? '—'}
                icon={UserCheck}
                description="Users with session activity"
              />
              <MetricCard
                title="Avg. session duration"
                value={
                  typeof stats.averageDurationSeconds === 'number'
                    ? `${Math.round(stats.averageDurationSeconds / 60)} min`
                    : '—'
                }
                icon={Clock}
                description="Mean length of sessions"
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
                <p className="text-sm text-gray-500 mt-1">
                  Live activity feed is not provided by the API; use Session Logs for history.
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {stats.recentActivity.length === 0 ? (
                    <p className="text-sm text-gray-500">No recent activity entries.</p>
                  ) : (
                    stats.recentActivity.map((activity, index) => (
                      <div key={index} className="flex items-center justify-between border-b pb-3 last:border-0 last:pb-0">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{activity.action}</p>
                          <p className="text-xs text-gray-500">User: {activity.userId}</p>
                        </div>
                        <p className="text-xs text-gray-500">{new Date(activity.timestamp).toLocaleString()}</p>
                      </div>
                    ))
                  )}
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
                              <span
                                className={cn(
                                  'px-2 py-1 rounded-full text-xs font-medium',
                                  user.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-emerald-100 text-emerald-800'
                                )}
                              >
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
                <p className="text-sm text-gray-500 mt-1">
                  Click a row to view transcript and feedback
                </p>
              </CardHeader>
              <CardContent>
                {sessionsLoading ? (
                  <p className="text-gray-500 py-8 text-center">Loading sessions…</p>
                ) : sessionsError ? (
                  <p className="text-red-600 py-8 text-center">{sessionsError}</p>
                ) : !sessionsData || sessionsData.sessions.length === 0 ? (
                  <p className="text-gray-500 py-8 text-center">No sessions found</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-2 font-medium">Session ID</th>
                          <th className="text-left py-2 font-medium">User ID</th>
                          <th className="text-left py-2 font-medium">Case ID</th>
                          <th className="text-left py-2 font-medium">Started</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sessionsData.sessions.map((s) => (
                          <tr
                            key={s.id}
                            onClick={() => handleSessionRowClick(s.id)}
                            className={cn(
                              'border-b cursor-pointer transition-colors',
                              selectedDetail?.session.id === s.id
                                ? 'bg-emerald-50'
                                : 'hover:bg-gray-50'
                            )}
                          >
                            <td className="py-2">{s.id}</td>
                            <td className="py-2">{s.user_id}</td>
                            <td className="py-2">{s.case_id}</td>
                            <td className="py-2">{new Date(s.started_at).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Session detail panel */}
            {selectedDetail && (
              <SessionDetailPanel
                detail={selectedDetail}
                onClose={clearSelectedSession}
              />
            )}
            {detailLoading && (
              <Card>
                <CardContent className="py-12 text-center text-gray-500">
                  Loading session detail…
                </CardContent>
              </Card>
            )}
            {detailError && !detailLoading && (
              <Card>
                <CardContent className="py-8 text-center text-red-600">
                  {detailError}
                </CardContent>
              </Card>
            )}
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
                        {stats.analyticsData.averageScoreByMonth.length === 0 ? (
                          <p className="text-sm text-gray-500">
                            Monthly score trends are not included in the admin aggregates API.
                          </p>
                        ) : (
                          <div className="space-y-2">
                            {stats.analyticsData.averageScoreByMonth.map((data, index) => (
                              <div key={index} className="flex items-center justify-between">
                                <span className="text-sm">{data.month}</span>
                                <div className="flex items-center gap-2">
                                  <div className="w-20 h-2 bg-gray-200 rounded-full">
                                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${data.score}%` }} />
                                  </div>
                                  <span className="text-sm font-medium">{data.score}%</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <div className="grid gap-6 lg:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle>Session share by case</CardTitle>
                      <p className="text-sm text-gray-500 mt-1">
                        Share of all sessions per case (from admin aggregates).
                      </p>
                    </CardHeader>
                    <CardContent>
                      {stats.analyticsData.completionRates.length === 0 ? (
                        <p className="text-sm text-gray-500">
                          No per-case session counts yet (backend may return an empty breakdown).
                        </p>
                      ) : (
                        <div className="space-y-3">
                          {stats.analyticsData.completionRates.map((data, index) => (
                            <div key={index} className="flex items-center justify-between">
                              <span className="text-sm capitalize">{data.difficulty}</span>
                              <div className="flex items-center gap-2">
                                <div className="w-16 h-2 bg-gray-200 rounded-full">
                                  <div className="h-full bg-green-500 rounded-full" style={{ width: `${data.rate * 100}%` }} />
                                </div>
                                <span className="text-sm font-medium">{Math.round(data.rate * 100)}%</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Cases by category</CardTitle>
                      <p className="text-sm text-gray-500 mt-1">From cohort case statistics.</p>
                    </CardHeader>
                    <CardContent>
                      {stats.analyticsData.commonChallenges.length === 0 ? (
                        <p className="text-sm text-gray-500">No category breakdown available.</p>
                      ) : (
                        <div className="space-y-2">
                          {stats.analyticsData.commonChallenges.map((challenge, index) => (
                            <div key={index} className="flex items-center justify-between text-sm">
                              <span>{challenge.challenge}</span>
                              <span className="font-medium">{challenge.frequency} cases</span>
                            </div>
                          ))}
                        </div>
                      )}
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
              <Button onClick={onCreateClick} className="flex items-center gap-2">
                <Plus className="h-4 w-4" />
                Create New Case
              </Button>
            </div>

            {caseLoading ? (
              <div className="text-gray-500">Loading cases…</div>
            ) : (
              <Card>
                <CardHeader>
                  <CardTitle>Cases</CardTitle>
                </CardHeader>
                <CardContent>
                  <CasesTable items={caseItems} onEdit={onEdit} onDelete={onDelete} />
                </CardContent>
              </Card>
            )}

            <CaseForm
              open={formOpen}
              onClose={() => setFormOpen(false)}
              mode={formMode}
              initial={editing ?? undefined}
              onSubmit={onSubmitForm}
              submitting={submitting}
            />
          </div>
        )

      case 'plugins':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Installed Plugins</h2>
              <Button variant="outline" size="sm" asChild>
                <a href="/docs/plugin-developer-guide" className="flex items-center gap-2">
                  <ExternalLink className="h-4 w-4" />
                  View Developer Docs
                </a>
              </Button>
            </div>

            {pluginsLoading ? (
              <p className="text-gray-500 py-8">Loading plugins…</p>
            ) : pluginsError ? (
              <p className="text-red-600 py-8">{pluginsError}</p>
            ) : (
              <div className="space-y-6">
                <div>
                  <h3 className="font-semibold">Patient Models</h3>
                  {installedPlugins?.patient_models?.length ? (
                    <div className="mt-2 space-y-2">
                      {installedPlugins.patient_models.map((p) => (
                        <div key={p.name} className="border rounded-lg p-3 bg-white shadow-sm">
                          <div className="font-medium text-gray-900">{p.name}</div>
                          <div className="text-sm text-gray-500">Version {p.version}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-sm mt-2">No patient model plugins registered.</p>
                  )}
                </div>

                <div>
                  <h3 className="font-semibold">Evaluators</h3>
                  {installedPlugins?.evaluators?.length ? (
                    <div className="mt-2 space-y-2">
                      {installedPlugins.evaluators.map((p) => (
                        <div key={p.name} className="border rounded-lg p-3 bg-white shadow-sm">
                          <div className="font-medium text-gray-900">{p.name}</div>
                          <div className="text-sm text-gray-500">Version {p.version}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-sm mt-2">No evaluator plugins registered.</p>
                  )}
                </div>

                <div>
                  <h3 className="font-semibold">Metrics Plugins</h3>
                  {installedPlugins?.metrics?.length ? (
                    <div className="mt-2 space-y-2">
                      {installedPlugins.metrics.map((p) => (
                        <div key={p.name} className="border rounded-lg p-3 bg-white shadow-sm">
                          <div className="font-medium text-gray-900">{p.name}</div>
                          <div className="text-sm text-gray-500">Version {p.version}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-sm mt-2">No metrics plugins registered.</p>
                  )}
                </div>
              </div>
            )}
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="h-screen flex flex-col">
      <Navbar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 overflow-y-auto md:ml-64">
          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            <nav className="mb-4 text-sm text-gray-500">
              Dashboard / <span className="text-gray-900">Admin</span>
            </nav>

            <div className="mb-8">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
                  <p className="mt-2 text-gray-600">Manage users, monitor sessions, and analyze platform performance</p>
                </div>
                <Button onClick={handleExportData} variant="outline" className="flex items-center gap-2">
                  <Download className="h-4 w-4" />
                  Export JSON
                </Button>
              </div>
            </div>

            {/* Tabs */}
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

            {renderTabContent()}
          </div>
        </main>
      </div>
    </div>
  )
}

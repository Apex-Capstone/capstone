/**
 * Root router: public routes, role-protected trainee/admin pages, and login redirect.
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { useAuthStore } from './store/authStore'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { CaseDetail } from './pages/CaseDetail'
import { Feedback } from './pages/Feedback'
import { Sessions } from './pages/Sessions'
import { SessionDetailPage } from './pages/SessionDetailPage'
import { Admin } from './pages/Admin'
import { Research } from './pages/Research'
import { ResearchSessions } from './pages/ResearchSessions'
import { PluginDeveloperGuide } from './pages/PluginDeveloperGuide'
import { ProtectedRoute } from './components/ProtectedRoute'

/**
 * Renders the login page or redirects authenticated users to the dashboard.
 *
 * @remarks
 * Prevents logged-in users from seeing `/login` again.
 *
 * @returns Login screen or a client-side redirect
 */
const LoginRoute = () => {
  const { isAuthenticated } = useAuthStore()

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }
  return <Login />
}

/**
 * Application route tree with {@link ProtectedRoute} wrappers for auth and roles.
 *
 * @returns Browser router wrapping all page routes
 */
function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-center" richColors />
      <Routes>
        {/* Public */}
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<LoginRoute />} />

        {/* Shared: admin + trainee */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute allowedRoles={['admin', 'trainee']}>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/case/:caseId"
          element={
            <ProtectedRoute allowedRoles={['admin', 'trainee']}>
              <CaseDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/feedback/:sessionId"
          element={
            <ProtectedRoute allowedRoles={['admin', 'trainee']}>
              <Feedback />
            </ProtectedRoute>
          }
        />
        <Route
          path="/sessions"
          element={
            <ProtectedRoute>
              <Sessions />
            </ProtectedRoute>
          }
        />
        <Route
          path="/sessions/:sessionId"
          element={
            <ProtectedRoute>
              <SessionDetailPage />
            </ProtectedRoute>
          }
        />

        {/* Admin routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <Admin />
            </ProtectedRoute>
          }
        />
        <Route
          path="/research"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <Research />
            </ProtectedRoute>
          }
        />
        <Route
          path="/research/sessions"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <ResearchSessions />
            </ProtectedRoute>
          }
        />
        <Route
          path="/docs/plugin-developer-guide"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <PluginDeveloperGuide />
            </ProtectedRoute>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

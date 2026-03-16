import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { CaseDetail } from './pages/CaseDetail'
import { Feedback } from './pages/Feedback'
import { Admin } from './pages/Admin'
import { Research } from './pages/Research'
import { PluginDeveloperGuide } from './pages/PluginDeveloperGuide'
import { ProtectedRoute } from './components/ProtectedRoute'

// Component to handle login route with redirect if already authenticated
const LoginRoute = () => {
  const { isAuthenticated } = useAuthStore()

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }
  return <Login />
}

function App() {
  return (
    <BrowserRouter>
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

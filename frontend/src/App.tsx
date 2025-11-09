import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { CaseDetail } from './pages/CaseDetail'
import { Feedback } from './pages/Feedback'
import { Admin } from './pages/Admin'
import { Research } from './pages/Research'
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

        {/* Authenticated */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/case/:caseId"
          element={
            <ProtectedRoute>
              <CaseDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/feedback/:sessionId"
          element={
            <ProtectedRoute>
              <Feedback />
            </ProtectedRoute>
          }
        />

        {/* Admin area: admin + instructor */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute allowedRoles={['admin', 'instructor']}>
              <Admin />
            </ProtectedRoute>
          }
        />

        {/* Research: admin + instructor (change/remove allowedRoles if you want all authenticated users) */}
        <Route
          path="/research"
          element={
            <ProtectedRoute allowedRoles={['admin', 'instructor']}>
              <Research />
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

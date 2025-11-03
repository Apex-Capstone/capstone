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
        {/* Root route - show home page */}
        <Route path="/" element={<Home />} />
        
        {/* Login route - redirect to dashboard if already authenticated */}
        <Route path="/login" element={<LoginRoute />} />
        
        {/* Protected routes */}
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
        
        {/* Admin route - requires admin role */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRole="admin">
              <Admin />
            </ProtectedRoute>
          }
        />
        
        {/* Research route - accessible to both roles */}
        <Route
          path="/research"
          element={
            <ProtectedRoute>
              <Research />
            </ProtectedRoute>
          }
        />
        
        {/* Catch-all route - redirect to root */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

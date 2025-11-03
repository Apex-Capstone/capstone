import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import type { ReactNode } from 'react'

interface ProtectedRouteProps {
  children: ReactNode
  requiredRole?: 'admin' | 'trainee'
}

export const ProtectedRoute = ({
  children,
  requiredRole,
}: ProtectedRouteProps) => {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requiredRole && user?.role !== requiredRole) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}


/**
 * Route wrapper that requires authentication and optional role membership.
 */
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import type { ReactNode } from 'react'

/**
 * Props for {@link ProtectedRoute}.
 *
 * @property children - Nested route element to render when allowed
 * @property allowedRoles - If set, user role must be one of these or redirect occurs
 */
interface ProtectedRouteProps {
  children: ReactNode
  allowedRoles?: ('admin' | 'trainee')[]
}

/**
 * Guards content behind login and optional role checks.
 *
 * @remarks
 * Unauthenticated users go to `/login`. Authenticated users with a disallowed role go to `/dashboard`.
 *
 * @param props - {@link ProtectedRouteProps}
 * @returns Children, a login redirect, or a dashboard redirect
 */
export const ProtectedRoute = ({
  children,
  allowedRoles,
}: ProtectedRouteProps) => {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && allowedRoles.length > 0 && user?.role && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

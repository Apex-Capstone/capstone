/**
 * Global authentication state persisted to `localStorage` for JWT access across reloads.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/** Application role used for route guards and UI affordances. */
export type Role = 'trainee' | 'admin'

/**
 * Logged-in user profile from the backend (with optional legacy `name`).
 */
export interface User {
  id?: number
  email: string
  role: Role
  full_name?: string
  name?: string
}

/**
 * Auth slice: token, user, and imperative login/logout setters.
 *
 * @remarks
 * Persisted under the name `auth-storage`. The Axios client reads `state.token` from this blob
 * to attach `Authorization` headers (see `api/client.ts`).
 */
interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  /**
   * Stores credentials after a successful login (does not call the API).
   *
   * @param token - JWT access token
   * @param user - Parsed user object from the login response
   */
  login: (token: string, user: User) => void
  /** Clears token and user and sets `isAuthenticated` to false. */
  logout: () => void
}

/**
 * Zustand hook for auth state, persisted with `persist` middleware.
 *
 * @returns Auth state and actions (`login`, `logout`)
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      login: (token, user) => set({ token, user, isAuthenticated: true }),
      logout: () => set({ token: null, user: null, isAuthenticated: false }),
    }),
    { name: 'auth-storage' }
  )
)

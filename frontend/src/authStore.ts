/**
 * Legacy Zustand auth store that performs login via `auth.api` inside the store.
 *
 * @remarks
 * The running app uses `store/authStore`. This module is retained for reference;
 * it shares the same `auth-storage` persist key and would conflict if imported alongside the active store.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { login as apiLogin } from '@/api/auth.api'

type Role = 'trainee' | 'admin'

interface AuthState {
  token?: string
  user?: { id: number; email: string; role: Role; full_name?: string }
  /**
   * Calls the login API and persists token + user on success.
   *
   * @param email - User email
   * @param password - User password
   */
  login: (email: string, password: string) => Promise<void>
  /** Clears persisted credentials. */
  logout: () => void
}

/**
 * Default-exported store hook (legacy).
 *
 * @returns Auth state with async `login` and synchronous `logout`
 */
const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: undefined,
      user: undefined,
      login: async (email, password) => {
        const res = await apiLogin(email, password)
        set({ token: res.access_token, user: res.user })
      },
      logout: () => set({ token: undefined, user: undefined }),
    }),
    { name: 'auth-storage' }
  )
)

export default useAuthStore

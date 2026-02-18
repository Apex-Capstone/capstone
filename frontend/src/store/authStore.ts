import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Role = 'trainee' | 'admin'

export interface User {
  id?: number            // optional: backend usually returns this
  email: string
  role: Role
  full_name?: string     // optional: backend field
  name?: string          // keep for legacy components
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  login: (token: string, user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      login: (token, user) => set({ token, user, isAuthenticated: true }),
      logout: () => set({ token: null, user: null, isAuthenticated: false }),
    }),
    { name: 'auth-storage' } // <- Axios interceptor reads state.token from this key
  )
)

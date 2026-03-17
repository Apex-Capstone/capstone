import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { login as apiLogin } from '@/api/auth.api'

type Role = 'trainee' | 'admin'

interface AuthState {
  token?: string
  user?: { id: number; email: string; role: Role; full_name?: string }
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

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

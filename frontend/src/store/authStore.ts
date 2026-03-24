import { create } from 'zustand'
import { supabase } from '@/lib/supabase'
import type { Session } from '@supabase/supabase-js'

export type Role = 'trainee' | 'admin'

export interface AppUser {
  id: number
  email: string
  role: Role
  full_name?: string
  name?: string
  gender?: string
  race?: string
  year_of_study?: string
}

interface AuthState {
  token: string | null
  user: AppUser | null
  isAuthenticated: boolean
  loading: boolean
  setSession: (session: Session | null) => void
  setUser: (user: AppUser | null) => void
  logout: () => Promise<void>
  initialize: () => Promise<void>
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  loading: true,

  setSession: (session) => {
    set({
      token: session?.access_token ?? null,
      isAuthenticated: !!session?.access_token,
    })
  },

  setUser: (user) => {
    set({ user })
  },

  logout: async () => {
    await supabase.auth.signOut()
    set({ token: null, user: null, isAuthenticated: false })
  },

  initialize: async () => {
    const { data } = await supabase.auth.getSession()
    const session = data.session

    set({
      token: session?.access_token ?? null,
      isAuthenticated: !!session?.access_token,
    })

    if (session?.access_token) {
      try {
        const { default: api } = await import('@/api/client')
        const { data: profile } = await api.get('/v1/auth/me')
        set({ user: profile })
      } catch {
        // Profile not available yet — user can still navigate
      }
    }

    set({ loading: false })

    supabase.auth.onAuthStateChange((_event, session) => {
      get().setSession(session)
    })
  },
}))

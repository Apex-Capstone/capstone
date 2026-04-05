import axios from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Session } from '@supabase/supabase-js'
import { useAuthStore } from '@/store/authStore'
import {
  apiGet,
  mockGetSession,
  mockOnAuthStateChange,
  mockSignOut,
  resetAuthTestMocks,
} from '@/test/authTestMocks'

function minimalSession(accessToken: string): Session {
  return { access_token: accessToken } as Session
}

function resetStoreForTest() {
  useAuthStore.setState({
    token: null,
    user: null,
    isAuthenticated: false,
    loading: false,
  })
}

describe('useAuthStore', () => {
  beforeEach(() => {
    resetAuthTestMocks()
    resetStoreForTest()
  })

  describe('setSession', () => {
    it('sets token and isAuthenticated when access_token is present', () => {
      useAuthStore.getState().setSession(minimalSession('jwt-123'))
      const s = useAuthStore.getState()
      expect(s.token).toBe('jwt-123')
      expect(s.isAuthenticated).toBe(true)
    })

    it('clears user when session becomes null', () => {
      useAuthStore.setState({
        user: { id: 1, email: 'a@b.com', role: 'trainee', full_name: 'A' },
        token: 't',
        isAuthenticated: true,
      })
      useAuthStore.getState().setSession(null)
      const s = useAuthStore.getState()
      expect(s.user).toBeNull()
      expect(s.token).toBeNull()
      expect(s.isAuthenticated).toBe(false)
    })
  })

  describe('setUser', () => {
    it('updates user without changing token', () => {
      useAuthStore.setState({ token: 't', isAuthenticated: true })
      useAuthStore.getState().setUser({ id: 2, email: 'b@b.com', role: 'admin', full_name: 'Admin' })
      const s = useAuthStore.getState()
      expect(s.user?.email).toBe('b@b.com')
      expect(s.user?.role).toBe('admin')
      expect(s.token).toBe('t')
    })
  })

  describe('logout', () => {
    it('calls supabase signOut and clears auth state', async () => {
      useAuthStore.setState({
        token: 't',
        user: { id: 1, email: 'a@b.com', role: 'trainee' },
        isAuthenticated: true,
      })
      await useAuthStore.getState().logout()
      expect(mockSignOut).toHaveBeenCalledOnce()
      const s = useAuthStore.getState()
      expect(s.token).toBeNull()
      expect(s.user).toBeNull()
      expect(s.isAuthenticated).toBe(false)
    })
  })

  describe('refreshProfile', () => {
    it('sets user to null when there is no token', async () => {
      useAuthStore.setState({ user: { id: 1, email: 'x@x.com', role: 'trainee' } })
      await useAuthStore.getState().refreshProfile()
      expect(apiGet).not.toHaveBeenCalled()
      expect(useAuthStore.getState().user).toBeNull()
    })

    it('loads profile from /v1/auth/me when token exists', async () => {
      const profile = {
        id: 9,
        email: 'me@example.com',
        role: 'trainee' as const,
        full_name: 'Test User',
      }
      useAuthStore.setState({ token: 'tok', isAuthenticated: true })
      apiGet.mockResolvedValue({ data: profile })

      await useAuthStore.getState().refreshProfile()

      expect(apiGet).toHaveBeenCalledWith('/v1/auth/me')
      const s = useAuthStore.getState()
      expect(s.user).toEqual(profile)
      expect(s.isAuthenticated).toBe(true)
    })

    it('logs out on 401 from /v1/auth/me', async () => {
      useAuthStore.setState({ token: 'bad', isAuthenticated: true })
      const err = new axios.AxiosError('Unauthorized')
      err.response = { status: 401 } as import('axios').AxiosResponse
      apiGet.mockRejectedValue(err)

      await useAuthStore.getState().refreshProfile()

      expect(mockSignOut).toHaveBeenCalledOnce()
      const s = useAuthStore.getState()
      expect(s.token).toBeNull()
      expect(s.user).toBeNull()
      expect(s.isAuthenticated).toBe(false)
    })

    it('logs out on 403 from /v1/auth/me', async () => {
      useAuthStore.setState({ token: 'tok', isAuthenticated: true })
      const err = new axios.AxiosError('Forbidden')
      err.response = { status: 403 } as import('axios').AxiosResponse
      apiGet.mockRejectedValue(err)

      await useAuthStore.getState().refreshProfile()

      expect(mockSignOut).toHaveBeenCalledOnce()
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    })

    it('keeps session but clears user on non-auth API errors', async () => {
      useAuthStore.setState({ token: 'tok', isAuthenticated: true })
      apiGet.mockRejectedValue(new Error('network'))

      await useAuthStore.getState().refreshProfile()

      expect(mockSignOut).not.toHaveBeenCalled()
      const s = useAuthStore.getState()
      expect(s.isAuthenticated).toBe(true)
      expect(s.token).toBe('tok')
      expect(s.user).toBeNull()
    })
  })

  describe('initialize', () => {
    it('ends with no session when getSession returns null', async () => {
      mockGetSession.mockResolvedValueOnce({ data: { session: null } })

      await useAuthStore.getState().initialize()

      const s = useAuthStore.getState()
      expect(s.loading).toBe(false)
      expect(s.isAuthenticated).toBe(false)
      expect(s.token).toBeNull()
      expect(apiGet).not.toHaveBeenCalled()
      expect(mockOnAuthStateChange).toHaveBeenCalled()
    })

    it('fetches profile when a session exists', async () => {
      const profile = {
        id: 1,
        email: 'u@u.com',
        role: 'trainee' as const,
        full_name: 'U',
      }
      mockGetSession.mockResolvedValueOnce({
        data: { session: minimalSession('access') },
      })
      apiGet.mockResolvedValue({ data: profile })

      await useAuthStore.getState().initialize()

      const s = useAuthStore.getState()
      expect(s.loading).toBe(false)
      expect(s.token).toBe('access')
      expect(s.user).toEqual(profile)
      expect(s.isAuthenticated).toBe(true)
      expect(apiGet).toHaveBeenCalledWith('/v1/auth/me')
    })

    it('runs refreshProfile when onAuthStateChange receives a new session', async () => {
      mockGetSession.mockResolvedValueOnce({ data: { session: null } })
      let authCallback: ((event: string, session: Session | null) => void) | undefined
      mockOnAuthStateChange.mockImplementationOnce((cb) => {
        authCallback = cb
        return { data: { subscription: { unsubscribe: vi.fn() } } }
      })

      const profile = {
        id: 3,
        email: 'n@n.com',
        role: 'trainee' as const,
        full_name: 'New',
      }
      apiGet.mockResolvedValue({ data: profile })

      await useAuthStore.getState().initialize()
      expect(authCallback).toBeDefined()

      apiGet.mockClear()
      await authCallback!('SIGNED_IN', minimalSession('after-verify'))

      expect(apiGet).toHaveBeenCalledWith('/v1/auth/me')
      expect(useAuthStore.getState().token).toBe('after-verify')
      expect(useAuthStore.getState().user).toEqual(profile)
    })
  })
})

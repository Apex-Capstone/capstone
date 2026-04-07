import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAuthGate } from '@/hooks/useAuthGate'
import { useAuthStore } from '@/store/authStore'
import { apiGet, resetAuthTestMocks } from '@/test/authTestMocks'

describe('useAuthGate', () => {
  beforeEach(() => {
    resetAuthTestMocks()
    useAuthStore.setState({
      token: null,
      user: null,
      isAuthenticated: false,
      loading: false,
    })
  })

  it("returns 'loading' while global auth loading is true", () => {
    useAuthStore.setState({ loading: true })
    const { result } = renderHook(() => useAuthGate())
    expect(result.current).toBe('loading')
  })

  it("returns 'public' when not authenticated", () => {
    const { result } = renderHook(() => useAuthGate())
    expect(result.current).toBe('public')
  })

  it("returns 'authed' when authenticated and user is already loaded", () => {
    useAuthStore.setState({
      loading: false,
      isAuthenticated: true,
      user: { id: 1, email: 'a@a.com', role: 'trainee', full_name: 'A' },
    })
    const { result } = renderHook(() => useAuthGate())
    expect(result.current).toBe('authed')
  })

  it("returns 'authed' after refreshProfile fills user (token without profile)", async () => {
    useAuthStore.setState({
      loading: false,
      isAuthenticated: true,
      user: null,
      token: 't',
    })
    apiGet.mockResolvedValue({
      data: {
        id: 1,
        email: 'sync@example.com',
        role: 'trainee' as const,
        full_name: 'Synced',
      },
    })

    const { result } = renderHook(() => useAuthGate())

    expect(result.current).toBe('loading')

    await waitFor(() => {
      expect(result.current).toBe('authed')
    })
    expect(useAuthStore.getState().user?.email).toBe('sync@example.com')
  })
})

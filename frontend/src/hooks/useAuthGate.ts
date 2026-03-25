import { useEffect, useState } from 'react'
import { useAuthStore } from '@/store/authStore'

/**
 * For routes that redirect when `isAuthenticated` is true: wait until `/v1/auth/me`
 * has been fetched (or attempted) so `user` is populated when possible — e.g. after
 * email verification in another tab while the signup tab still has a stale store.
 */
export function useAuthGate(): 'loading' | 'public' | 'authed' {
  const loading = useAuthStore((s) => s.loading)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const user = useAuthStore((s) => s.user)
  const refreshProfile = useAuthStore((s) => s.refreshProfile)
  const [profileFetchDone, setProfileFetchDone] = useState(false)

  useEffect(() => {
    if (loading) return
    if (!isAuthenticated) {
      setProfileFetchDone(true)
      return
    }
    if (user) {
      setProfileFetchDone(true)
      return
    }
    setProfileFetchDone(false)
    let cancelled = false
    void refreshProfile().finally(() => {
      if (!cancelled) setProfileFetchDone(true)
    })
    return () => {
      cancelled = true
    }
  }, [loading, isAuthenticated, user, refreshProfile])

  if (loading) return 'loading'
  if (isAuthenticated && !user && !profileFetchDone) return 'loading'
  if (isAuthenticated) return 'authed'
  return 'public'
}

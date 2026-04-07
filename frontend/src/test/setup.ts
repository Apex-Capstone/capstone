import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'
import {
  apiGet,
  mockGetSession,
  mockOnAuthStateChange,
  mockSignOut,
} from './authTestMocks'

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: () => mockGetSession(),
      signOut: () => mockSignOut(),
      onAuthStateChange: (cb: (event: string, session: import('@supabase/supabase-js').Session | null) => void) =>
        mockOnAuthStateChange(cb),
    },
  },
}))

vi.mock('@/api/client', () => ({
  default: {
    get: (...args: unknown[]) => apiGet(...args),
  },
}))

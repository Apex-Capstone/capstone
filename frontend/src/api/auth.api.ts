/**
 * Authentication API helpers using the shared Axios client.
 */
import api from '@/api/client'

/** Raw login response body from `POST /v1/auth/login`. */
export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  user: {
    id: number
    email: string
    role: 'trainee' | 'admin'
    full_name?: string
  }
}

/**
 * Authenticates with email and password and returns the wire-format response.
 *
 * @remarks
 * The Zustand `useAuthStore` hook persists tokens separately; this function only performs the HTTP call.
 *
 * @param email - User email
 * @param password - Plain-text password
 * @returns Parsed {@link LoginResponse} including `access_token` and `user`
 */
export const login = async (email: string, password: string) => {
  const { data } = await api.post<LoginResponse>('/v1/auth/login', { email, password })
  return data
}

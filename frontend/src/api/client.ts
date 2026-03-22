/**
 * Shared Axios instance for the backend API.
 *
 * @remarks
 * Base URL comes from `import.meta.env.VITE_API_URL` or defaults to `http://localhost:8000`.
 * A request interceptor reads the JWT from `localStorage` under the Zustand persist key
 * `auth-storage` and sets `Authorization: Bearer <token>`.
 */
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

/**
 * Ensures authenticated requests include the persisted bearer token when present.
 *
 * @remarks
 * Parses `auth-storage` JSON and reads `state.token` or legacy `token`. Swallow parse errors.
 *
 * @param config - Axios request config being sent
 * @returns The same config, possibly with `Authorization` header set
 */
apiClient.interceptors.request.use((config) => {
  const raw = localStorage.getItem('auth-storage')
  if (raw) {
    try {
      const parsed = JSON.parse(raw)
      const token = parsed?.state?.token ?? parsed?.token
      if (token) {
        config.headers = config.headers ?? {}
        config.headers.Authorization = `Bearer ${token}`
      }
    } catch {}
  }
  return config
})

/**
 * Calls the login endpoint and returns a normalized token + user payload.
 *
 * @remarks
 * Kept on the default client so `auth.api` login helpers and login pages can share the same Axios instance.
 *
 * @param email - User email
 * @param password - Plain-text password
 * @returns Object with `token` (access token string) and `user` from the API
 */
export const loginUser = async (email: string, password: string) => {
  const { data } = await apiClient.post('/v1/auth/login', { email, password })
  return {
    token: data.access_token,
    user: data.user,
  }
}

export default apiClient

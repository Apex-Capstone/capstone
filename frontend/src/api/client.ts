import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// attach JWT from persisted store/localStorage
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

// on 401 (expired/invalid token), clear auth and redirect to login
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ---- Auth (keep here so Login.tsx can import it) ----
export const loginUser = async (email: string, password: string) => {
  const { data } = await apiClient.post('/v1/auth/login', { email, password })
  return {
    token: data.access_token,
    user: data.user,
  }
}


export default apiClient

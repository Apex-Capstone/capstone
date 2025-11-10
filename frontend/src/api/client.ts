import axios from 'axios'

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

// ---- Auth (keep here so Login.tsx can import it) ----
export const loginUser = async (email: string, password: string) => {
  const { data } = await apiClient.post('/v1/auth/login', { email, password })
  return {
    token: data.access_token,
    user: data.user,
  }
}


export default apiClient

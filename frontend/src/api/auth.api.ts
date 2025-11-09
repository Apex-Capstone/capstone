import api from '@/api/client'

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  user: {
    id: number
    email: string
    role: 'student' | 'instructor' | 'admin'
    full_name?: string
  }
}

export const login = async (email: string, password: string) => {
  const { data } = await api.post<LoginResponse>('/v1/auth/login', { email, password })
  return data
}

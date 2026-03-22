import api from '@/api/client'
import type { Case, CaseDTO, CaseListDTO } from '@/types/case'
import { caseFromDTO, toCreatePayload, toUpdatePayload } from '@/adapters/case.adapter'

const BASE = '/v1/cases'

export const listCases = async (opts?: {
  offset?: number; limit?: number; difficulty?: string; category?: string
}): Promise<{ items: Case[]; total: number }> => {
  const { offset = 0, limit = 20, difficulty, category } = opts ?? {}
  const res = await api.get<CaseListDTO | CaseDTO[]>(BASE, {
    params: { skip: offset, limit, difficulty, category }
  })

  // Accept both shapes
  const data = res.data as any
  if (Array.isArray(data)) {
    return { items: data.map(caseFromDTO), total: data.length }
  }
  return { items: data.cases.map(caseFromDTO), total: data.total }
}


export const getCase = async (id: number): Promise<Case> => {
  const res = await api.get<CaseDTO>(`${BASE}/${id}`)
  return caseFromDTO(res.data)
}

export const createCase = async (data: Partial<Case>): Promise<Case> => {
  const res = await api.post<CaseDTO>(BASE, toCreatePayload(data))
  return caseFromDTO(res.data)
}

export const updateCase = async (id: number, changes: Partial<Case>): Promise<Case> => {
  const res = await api.patch<CaseDTO>(`${BASE}/${id}`, toUpdatePayload(changes))
  return caseFromDTO(res.data)
}

export const deleteCase = async (id: number): Promise<void> => {
  await api.delete(`${BASE}/${id}`)
}

/**
 * Case (scenario) CRUD and listing against `/v1/cases`.
 */
import api from '@/api/client'
import type { Case, CaseDTO, CaseListDTO } from '@/types/case'
import { caseFromDTO, toCreatePayload, toUpdatePayload } from '@/adapters/case.adapter'

const BASE = '/v1/cases'

/**
 * Lists cases with optional filters and pagination.
 *
 * @remarks
 * Accepts either a paginated `{ cases, total }` body or a raw array from the API.
 *
 * @param opts - Optional `offset`, `limit`, `difficulty`, and `category` query params
 * @returns Domain cases and total count
 */
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

/**
 * Loads a single case by id.
 *
 * @param id - Case primary key
 * @returns Domain {@link Case}
 */
export const getCase = async (id: number): Promise<Case> => {
  const res = await api.get<CaseDTO>(`${BASE}/${id}`)
  return caseFromDTO(res.data)
}

/**
 * Creates a new case from partial domain fields.
 *
 * @param data - Required fields per {@link toCreatePayload}
 * @returns Created case as {@link Case}
 */
export const createCase = async (data: Partial<Case>): Promise<Case> => {
  const res = await api.post<CaseDTO>(BASE, toCreatePayload(data))
  return caseFromDTO(res.data)
}

/**
 * Partially updates an existing case.
 *
 * @param id - Case primary key
 * @param changes - Partial domain fields to patch
 * @returns Updated {@link Case}
 */
export const updateCase = async (id: number, changes: Partial<Case>): Promise<Case> => {
  const res = await api.patch<CaseDTO>(`${BASE}/${id}`, toUpdatePayload(changes))
  return caseFromDTO(res.data)
}

/**
 * Deletes a case by id.
 *
 * @param id - Case primary key
 * @returns Resolves when the server returns success
 */
export const deleteCase = async (id: number): Promise<void> => {
  await api.delete(`${BASE}/${id}`)
}

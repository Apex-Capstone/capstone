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



// const generateMockMessages = (caseId: string): Message[] => {
//   // SPIKES-focused dialogue examples
//   const spikesDialogue = {
//     '1': [
//       {
//         id: '1',
//         role: 'assistant' as const,
//         content: 'I have the test results back from your biopsy. Before we discuss them, I want to make sure you understand what we were looking for. What is your understanding of why we did the biopsy?',
//         timestamp: '2024-01-15T10:05:00Z',
//       },
//       {
//         id: '2',
//         role: 'user' as const,
//         content: 'I know you were checking to see if the lump was cancerous. I\'ve been really worried about it.',
//         timestamp: '2024-01-15T10:06:00Z',
//       },
//       {
//         id: '3',
//         role: 'assistant' as const,
//         content: 'I can see that this has been weighing heavily on you. Your concerns are completely understandable. The results show that the tissue is malignant - meaning it is cancer. I know this is difficult news to hear.',
//         timestamp: '2024-01-15T10:07:00Z',
//       },
//     ],
//     '2': [
//       {
//         id: '1',
//         role: 'assistant' as const,
//         content: 'I understand you\'re upset about the treatment plan we discussed. Can you help me understand what\'s concerning you the most?',
//         timestamp: '2024-01-14T09:05:00Z',
//       },
//       {
//         id: '2',
//         role: 'user' as const,
//         content: 'This is ridiculous! You\'re telling me I need surgery but you can\'t even guarantee it will work. Why should I put myself through that?',
//         timestamp: '2024-01-14T09:06:00Z',
//       },
//       {
//         id: '3',
//         role: 'assistant' as const,
//         content: 'I can hear how frustrated and scared you are. These feelings are completely valid - facing surgery is a big decision. Let\'s talk about your specific concerns and make sure you have all the information you need.',
//         timestamp: '2024-01-14T09:07:00Z',
//       },
//     ],
//     default: [
//       {
//         id: '1',
//         role: 'assistant' as const,
//         content: 'Thank you for coming in today. I want to make sure we have privacy and won\'t be interrupted. Is it okay if we discuss your recent test results?',
//         timestamp: '2024-01-13T11:05:00Z',
//       },
//       {
//         id: '2',
//         role: 'user' as const,
//         content: 'Yes, I\'ve been waiting to hear about them. What did you find?',
//         timestamp: '2024-01-13T11:06:00Z',
//       },
//     ]
//   }
  
//   return spikesDialogue[caseId as keyof typeof spikesDialogue] || spikesDialogue.default
// }

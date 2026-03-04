import api from '@/api/client'
import type {
  SessionDTO,
  SessionListDTO,
  TurnResponseWithAudioDTO,
  SessionDetailDTO,
} from '@/types/session'
import {
  sessionFromDTO,
  sessionListFromDTO,
  turnResponseWithAudioFromDTO,
  sessionDetailFromDTO,
  toSessionCreatePayload,
  toTurnCreatePayload,
} from '@/adapters/session.adapter'
import type { Session, SessionList, TurnResponseWithAudio, SessionDetail } from '@/types/session'

const BASE = '/v1/sessions'

/**
 * Create a new session for a case
 */
export const createSession = async (caseId: number): Promise<Session> => {
  const res = await api.post<SessionDTO>(BASE, toSessionCreatePayload(caseId))
  return sessionFromDTO(res.data)
}

/**
 * Submit a text turn and get patient response
 */
export const submitTurn = async (
  sessionId: number,
  text: string,
  audioUrl?: string
): Promise<TurnResponseWithAudio> => {
  const res = await api.post<TurnResponseWithAudioDTO>(
    `${BASE}/${sessionId}/turns`,
    toTurnCreatePayload(text, audioUrl)
  )
  return turnResponseWithAudioFromDTO(res.data)
}

/**
 * Get session details including turns
 */
export const getSession = async (sessionId: number): Promise<SessionDetail> => {
  const res = await api.get<SessionDetailDTO>(`${BASE}/${sessionId}`)
  return sessionDetailFromDTO(res.data)
}

/**
 * Close a session and get feedback
 */
export const closeSession = async (sessionId: number): Promise<any> => {
  const res = await api.post(`${BASE}/${sessionId}:close`)
  return res.data
}

/**
 * List all sessions for the current user
 */
export const listSessions = async (skip = 0, limit = 100): Promise<SessionList> => {
  const res = await api.get<SessionListDTO>(BASE, { params: { skip, limit } })
  return sessionListFromDTO(res.data)
}

/**
 * Upload audio file for a turn
 */
export const submitAudioTurn = async (
  sessionId: number,
  audioFile: File
): Promise<TurnResponseWithAudio> => {
  const formData = new FormData()
  formData.append('audio_file', audioFile)
  
  const res = await api.post<TurnResponseWithAudioDTO>(
    `${BASE}/${sessionId}/audio`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )
  return turnResponseWithAudioFromDTO(res.data)
}


import api from '@/api/client'
import type {
  Session,
  SessionDTO,
  SessionDetail,
  SessionDetailDTO,
  SessionListResponse,
  SessionListResponseDTO,
  TurnResponseWithAudio,
  TurnResponseWithAudioDTO,
} from '@/types/session'
import {
  sessionFromDTO,
  turnResponseWithAudioFromDTO,
  sessionDetailFromDTO,
  sessionListFromDTO,
  toSessionCreatePayload,
  toTurnCreatePayload,
} from '@/adapters/session.adapter'

const BASE = '/v1/sessions'

/**
 * Create a new session for a case
 */
export const createSession = async (
  caseId: number,
  opts?: { forceNew?: boolean }
): Promise<Session> => {
  const { forceNew = false } = opts ?? {}
  const res = await api.post<SessionDTO>(BASE, toSessionCreatePayload(caseId, forceNew))
  return sessionFromDTO(res.data)
}

/**
 * Submit a text turn and get patient response
 */
export const submitTurn = async (
  sessionId: number,
  text: string,
  audioUrl?: string,
  enableTts = false,
): Promise<TurnResponseWithAudio> => {
  const res = await api.post<TurnResponseWithAudioDTO>(
    `${BASE}/${sessionId}/turns`,
    toTurnCreatePayload(text, audioUrl, enableTts)
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
 * List sessions for the current user
 */
export const listUserSessions = async (opts?: {
  skip?: number
  limit?: number
}): Promise<SessionListResponse> => {
  const { skip = 0, limit = 10 } = opts ?? {}
  const res = await api.get<SessionListResponseDTO>(BASE, {
    params: { skip, limit },
  })
  return sessionListFromDTO(res.data)
}

/**
 * Close a session and get feedback
 */
export const closeSession = async (sessionId: number): Promise<any> => {
  const res = await api.post(`${BASE}/${sessionId}:close`)
  return res.data
}

/**
 * Upload audio file for a turn
 */
export const submitAudioTurn = async (
  sessionId: number,
  audioFile: File,
  enableTts = false,
): Promise<TurnResponseWithAudio> => {
  const formData = new FormData()
  formData.append('audio_file', audioFile)
  formData.append('enable_tts', String(enableTts))
  
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

export interface AudioTranscriptionResult {
  transcript: string
}

/**
 * Upload audio file and return only the transcript.
 */
export const transcribeAudioTurn = async (
  sessionId: number,
  audioFile: File
): Promise<AudioTranscriptionResult> => {
  const formData = new FormData()
  formData.append('audio_file', audioFile)

  const res = await api.post<{ transcript: string }>(
    `${BASE}/${sessionId}/audio:transcribe`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )

  return {
    transcript: res.data.transcript,
  }
}


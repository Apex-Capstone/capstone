/**
 * Session lifecycle, turns, audio upload, and transcription API.
 */
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
  sessionListFromDTO,
  turnResponseWithAudioFromDTO,
  sessionDetailFromDTO,
  toSessionCreatePayload,
  toTurnCreatePayload,
} from '@/adapters/session.adapter'

const BASE = '/v1/sessions'

/**
 * Creates a new training session for a case.
 *
 * @param caseId - Case to start
 * @param opts - Optional `forceNew` to start a fresh session even if one exists
 * @returns Domain {@link Session}
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
 * Submits a text turn and returns the patient reply (and optional audio URLs).
 *
 * @param sessionId - Active session id
 * @param text - Trainee message text
 * @param audioUrl - Optional prior audio URL if applicable
 * @param enableTts - When true, request assistant TTS audio when supported
 * @returns Normalized {@link TurnResponseWithAudio}
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
 * Loads session detail including full turn history.
 *
 * @param sessionId - Session id
 * @returns {@link SessionDetail} with nested turns
 */
export const getSession = async (sessionId: number): Promise<SessionDetail> => {
  const res = await api.get<SessionDetailDTO>(`${BASE}/${sessionId}`)
  return sessionDetailFromDTO(res.data)
}

/**
 * Lists sessions for the authenticated user with pagination.
 *
 * @param opts - Optional `skip` and `limit`
 * @returns Sessions and total count
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
 * Closes a session and triggers server-side feedback generation.
 *
 * @param sessionId - Session to close
 * @returns Raw API payload (shape varies by backend)
 */
export const closeSession = async (sessionId: number): Promise<any> => {
  const res = await api.post(`${BASE}/${sessionId}:close`)
  return res.data
}

/**
 * Lists sessions for the current user (legacy pagination defaults).
 *
 * @remarks
 * Prefer {@link listUserSessions} for explicit options; this keeps older call sites working.
 *
 * @param skip - Offset (default 0)
 * @param limit - Page size (default 100)
 * @returns {@link SessionListResponse}
 */
export const listSessions = async (
  skip = 0,
  limit = 100
): Promise<SessionListResponse> => {
  const res = await api.get<SessionListResponseDTO>(BASE, { params: { skip, limit } })
  return sessionListFromDTO(res.data)
}

/**
 * Submits an audio file for a turn and returns the patient response.
 *
 * @param sessionId - Active session id
 * @param audioFile - Recorded audio blob as `File`
 * @param enableTts - Request assistant TTS when supported
 * @returns {@link TurnResponseWithAudio}
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

/** Result of audio-only transcription without advancing the dialogue. */
export interface AudioTranscriptionResult {
  transcript: string
}

/**
 * Uploads audio and returns a transcript only (no full turn response).
 *
 * @param sessionId - Active session id
 * @param audioFile - Audio file to transcribe
 * @returns Transcript string wrapper
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

/**
 * Fetches assistant audio as a blob and returns an object URL for playback.
 *
 * @remarks
 * Caller should {@link URL.revokeObjectURL} when done to avoid leaks.
 *
 * @param audioUrl - Absolute or API-relative audio URL
 * @returns Blob object URL string
 */
export const fetchAssistantAudioObjectUrl = async (audioUrl: string): Promise<string> => {
  const res = await api.get<Blob>(audioUrl, {
    responseType: 'blob',
  })
  return URL.createObjectURL(res.data)
}

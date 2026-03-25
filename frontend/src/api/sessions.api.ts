/**
 * Session lifecycle, turns, audio upload, and transcription API.
 */
import api from '@/api/client'
import type {
  AudioToneAnalysis,
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
  audioToneFromDTO,
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
 */
export const submitTurn = async (
  sessionId: number,
  text: string,
  audioUrl?: string,
  enableTts = false,
  voiceTone?: AudioToneAnalysis,
): Promise<TurnResponseWithAudio> => {
  const res = await api.post<TurnResponseWithAudioDTO>(
    `${BASE}/${sessionId}/turns`,
    toTurnCreatePayload(text, audioUrl, enableTts, voiceTone)
  )
  return turnResponseWithAudioFromDTO(res.data)
}

/**
 * Loads session detail including full turn history.
 */
export const getSession = async (sessionId: number): Promise<SessionDetail> => {
  const res = await api.get<SessionDetailDTO>(`${BASE}/${sessionId}`)
  return sessionDetailFromDTO(res.data)
}

/**
 * List the current user's active sessions.
 */
export const listActiveSessions = async (opts?: {
  skip?: number
  limit?: number
}): Promise<SessionListResponse> => {
  const { skip = 0, limit = 100 } = opts ?? {}
  const res = await api.get<SessionListResponseDTO>(BASE, {
    params: { state: 'active', skip, limit },
  })
  return sessionListFromDTO(res.data)
}

/**
 * List the current user's completed (previous) sessions.
 */
export const listCompletedSessions = async (opts?: {
  skip?: number
  limit?: number
}): Promise<SessionListResponse> => {
  const { skip = 0, limit = 100 } = opts ?? {}
  const res = await api.get<SessionListResponseDTO>(BASE, {
    params: { state: 'completed', skip, limit },
  })
  return sessionListFromDTO(res.data)
}

/**
 * Closes a session and triggers server-side feedback generation.
 */
export const closeSession = async (sessionId: number): Promise<any> => {
  const res = await api.post(`${BASE}/${sessionId}:close`)
  return res.data
}

/**
 * Submits an audio file for a turn and returns the patient response.
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
  audioTone?: AudioToneAnalysis
}

/**
 * Uploads audio and returns a transcript only (no full turn response).
 */
export const transcribeAudioTurn = async (
  sessionId: number,
  audioFile: File
): Promise<AudioTranscriptionResult> => {
  const formData = new FormData()
  formData.append('audio_file', audioFile)

  const res = await api.post<{ transcript: string; audio_tone?: TurnResponseWithAudioDTO['audio_tone'] }>(
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
    audioTone: audioToneFromDTO(res.data.audio_tone),
  }
}

/**
 * Fetches assistant audio as a blob and returns an object URL for playback.
 */
export const fetchAssistantAudioObjectUrl = async (audioUrl: string): Promise<string> => {
  const res = await api.get<Blob>(audioUrl, {
    responseType: 'blob',
  })
  return URL.createObjectURL(res.data)
}

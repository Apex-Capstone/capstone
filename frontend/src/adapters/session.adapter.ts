/**
 * Maps session and turn DTOs to domain models and builds request payloads for `/v1/sessions`.
 */
import type {
  Session,
  SessionDTO,
  SessionDetail,
  SessionDetailDTO,
  Turn,
  TurnDTO,
  TurnResponseWithAudio,
  TurnResponseWithAudioDTO,
  SessionListResponse,
  SessionListResponseDTO,
} from '@/types/session'

/**
 * Converts a session DTO to the camelCase {@link Session} model.
 *
 * @param dto - Wire-format session row
 * @returns Domain session
 */
export function sessionFromDTO(dto: SessionDTO): Session {
  return {
    id: dto.id,
    userId: dto.user_id,
    caseId: dto.case_id,
    state: dto.state,
    currentSpikesStage: dto.current_spikes_stage ?? undefined,
    startedAt: dto.started_at,
    endedAt: dto.ended_at ?? undefined,
    durationSeconds: dto.duration_seconds,
    meta: dto.meta ?? undefined,
    caseTitle: dto.case_title ?? undefined,
    status: dto.status,
  }
}

/**
 * Converts a single turn DTO to {@link Turn}.
 *
 * @remarks
 * Reads optional `spans_json` via a loose cast when present on the DTO.
 *
 * @param dto - Wire-format turn
 * @returns Domain turn
 */
export function turnFromDTO(dto: TurnDTO): Turn {
  return {
    id: dto.id,
    sessionId: dto.session_id,
    turnNumber: dto.turn_number,
    role: dto.role,
    text: dto.text,
    audioUrl: dto.audio_url ?? undefined,
    metricsJson: dto.metrics_json ?? undefined,
    spikesStage: dto.spikes_stage ?? undefined,
    timestamp: dto.timestamp,
    spansJson: (dto as any).spans_json ?? undefined,
  }
}

/**
 * Maps a turn response DTO including nested turn + audio fields.
 *
 * @param dto - API response for `POST .../turns` or audio endpoints
 * @returns {@link TurnResponseWithAudio}
 */
export function turnResponseWithAudioFromDTO(dto: TurnResponseWithAudioDTO): TurnResponseWithAudio {
  return {
    turn: turnFromDTO(dto.turn),
    patientReply: dto.patient_reply,
    transcript: dto.transcript ?? undefined,
    audioUrl: dto.audio_url ?? undefined,
    assistantAudioUrl: dto.assistant_audio_url ?? undefined,
    spikesStage: dto.spikes_stage ?? undefined,
  }
}

/**
 * Maps session detail DTO including mapped `turns` array.
 *
 * @param dto - Wire-format session with turns
 * @returns {@link SessionDetail}
 */
export function sessionDetailFromDTO(dto: SessionDetailDTO): SessionDetail {
  return {
    ...sessionFromDTO(dto),
    turns: dto.turns.map(turnFromDTO),
  }
}

/**
 * Maps a paginated list of session DTOs.
 *
 * @param dto - Wire list response
 * @returns {@link SessionListResponse}
 */
export function sessionListFromDTO(dto: SessionListResponseDTO): SessionListResponse {
  return {
    sessions: dto.sessions.map(sessionFromDTO),
    total: dto.total,
  }
}

/**
 * JSON body for `POST /v1/sessions` when starting a session.
 *
 * @param caseId - Case to bind
 * @param forceNew - When true, discard in-progress session for this case if supported
 * @returns Serialized create payload
 */
export function toSessionCreatePayload(caseId: number, forceNew?: boolean) {
  return {
    case_id: caseId,
    force_new: forceNew ?? false,
  }
}

/**
 * JSON body for submitting a text turn.
 *
 * @param text - Trainee message
 * @param audioUrl - Optional audio URL reference
 * @param enableTts - Request TTS audio for assistant reply
 * @returns Serialized turn payload
 */
export function toTurnCreatePayload(text: string, audioUrl?: string, enableTts = false) {
  return {
    text,
    audio_url: audioUrl,
    enable_tts: enableTts,
  }
}

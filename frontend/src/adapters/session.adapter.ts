/**
 * Maps session and turn DTOs to domain models and builds request payloads for `/v1/sessions`.
 */
import type {
  AudioToneAnalysis,
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

export function audioToneFromDTO(dto?: TurnResponseWithAudioDTO['audio_tone']): AudioToneAnalysis | undefined {
  if (!dto) return undefined

  return {
    primary: dto.primary,
    secondary: dto.secondary ?? undefined,
    confidence: dto.confidence,
    dimensions: {
      valence: dto.dimensions?.valence ?? undefined,
      arousal: dto.dimensions?.arousal ?? undefined,
      paceWpm: dto.dimensions?.pace_wpm ?? undefined,
      volumeDb: dto.dimensions?.volume_db ?? undefined,
      pitchHz: dto.dimensions?.pitch_hz ?? undefined,
      jitter: dto.dimensions?.jitter ?? undefined,
      shimmer: dto.dimensions?.shimmer ?? undefined,
      pausesPerMin: dto.dimensions?.pauses_per_min ?? undefined,
    },
    labels: dto.labels ?? [],
    provider: dto.provider,
  }
}

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
    audioTone: audioToneFromDTO(dto.audio_tone),
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
export function toTurnCreatePayload(
  text: string,
  audioUrl?: string,
  enableTts = false,
  voiceTone?: AudioToneAnalysis
) {
  return {
    text,
    audio_url: audioUrl,
    enable_tts: enableTts,
    voice_tone: voiceTone
      ? {
          primary: voiceTone.primary,
          secondary: voiceTone.secondary,
          confidence: voiceTone.confidence,
          dimensions: {
            valence: voiceTone.dimensions.valence,
            arousal: voiceTone.dimensions.arousal,
            pace_wpm: voiceTone.dimensions.paceWpm,
            volume_db: voiceTone.dimensions.volumeDb,
            pitch_hz: voiceTone.dimensions.pitchHz,
            jitter: voiceTone.dimensions.jitter,
            shimmer: voiceTone.dimensions.shimmer,
            pauses_per_min: voiceTone.dimensions.pausesPerMin,
          },
          labels: voiceTone.labels,
          provider: voiceTone.provider,
        }
      : undefined,
  }
}

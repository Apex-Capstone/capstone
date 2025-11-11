import type {
  Session,
  SessionDTO,
  Turn,
  TurnDTO,
  TurnResponseWithAudio,
  TurnResponseWithAudioDTO,
  SessionDetail,
  SessionDetailDTO,
} from '@/types/session'

// Convert backend DTO to frontend model
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
  }
}

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
  }
}

export function turnResponseWithAudioFromDTO(dto: TurnResponseWithAudioDTO): TurnResponseWithAudio {
  return {
    turn: turnFromDTO(dto.turn),
    patientReply: dto.patient_reply,
    audioUrl: dto.audio_url ?? undefined,
    spikesStage: dto.spikes_stage ?? undefined,
  }
}

export function sessionDetailFromDTO(dto: SessionDetailDTO): SessionDetail {
  return {
    ...sessionFromDTO(dto),
    turns: dto.turns.map(turnFromDTO),
  }
}

// Convert frontend model to backend create payload
export function toSessionCreatePayload(caseId: number) {
  return {
    case_id: caseId,
  }
}

export function toTurnCreatePayload(text: string, audioUrl?: string) {
  return {
    text,
    audio_url: audioUrl,
  }
}


// Common chat message type
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  source?: 'text' | 'audio'
  status?: 'pending' | 'sent' | 'error'
  assistantAudioUrl?: string
}

// Wire types that match backend responses (snake_case)
export interface SessionDTO {
  id: number
  user_id: number
  case_id: number
  state: string
  current_spikes_stage?: string | null
  started_at: string
  ended_at?: string | null
  duration_seconds: number
  meta?: string | null
  case_title?: string | null
  /** Computed by API: "active" | "closed" (closed when ended_at is set) */
  status: 'active' | 'closed'
}

export interface TurnDTO {
  id: number
  session_id: number
  turn_number: number
  role: string
  text: string
  audio_url?: string | null
  metrics_json?: string | null
  spikes_stage?: string | null
  timestamp: string
  spans_json?: string | null
}

export interface TurnResponseWithAudioDTO {
  turn: TurnDTO
  patient_reply: string
  transcript?: string | null
  audio_url?: string | null
  assistant_audio_url?: string | null
  spikes_stage?: string | null
}

export interface SessionDetailDTO extends SessionDTO {
  turns: TurnDTO[]
}

// UI types (camelCase for the app)
export interface Session {
  id: number
  userId: number
  caseId: number
  state: string
  currentSpikesStage?: string
  startedAt: string
  endedAt?: string
  durationSeconds: number
  meta?: string
  caseTitle?: string
  /** From API: "active" | "closed" */
  status: 'active' | 'closed'
}

export interface Turn {
  id: number
  sessionId: number
  turnNumber: number
  role: string
  text: string
  audioUrl?: string
  metricsJson?: string
  spikesStage?: string
  timestamp: string
  spansJson?: string
}

export interface TurnResponseWithAudio {
  turn: Turn
  patientReply: string
  transcript?: string
  audioUrl?: string
  assistantAudioUrl?: string
  spikesStage?: string
}

export interface SessionDetail extends Session {
  turns: Turn[]
}

export interface SessionListResponseDTO {
  sessions: SessionDTO[]
  total: number
}

export interface SessionListResponse {
  sessions: Session[]
  total: number
}


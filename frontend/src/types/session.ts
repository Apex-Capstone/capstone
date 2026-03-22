/**
 * Session, turn, and chat message types for the training UI and API adapters.
 *
 * @remarks
 * {@link SessionDTO} and related `*DTO` types mirror backend JSON (`snake_case`).
 * Domain types such as {@link Session} use `camelCase` in the app.
 */

/** Single chat message in the research or session UI. */
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  /** Whether the message came from typed text or audio. */
  source?: 'text' | 'audio'
  /** Delivery state for optimistic UI. */
  status?: 'pending' | 'sent' | 'error'
  assistantAudioUrl?: string
}

/** Wire shape for a session row as returned by the API (`snake_case`). */
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
  /** Set on admin session endpoints from the users table */
  user_email?: string | null
  user_full_name?: string | null
  /** Computed by API: "active" | "closed" (closed when ended_at is set) */
  status: 'active' | 'closed'
}

/** Wire shape for one turn in a session. */
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

/** API response when submitting a turn that may include TTS audio. */
export interface TurnResponseWithAudioDTO {
  turn: TurnDTO
  patient_reply: string
  transcript?: string | null
  audio_url?: string | null
  assistant_audio_url?: string | null
  spikes_stage?: string | null
}

/** Session detail including full turn list (`snake_case` wire type). */
export interface SessionDetailDTO extends SessionDTO {
  turns: TurnDTO[]
}

/** Session row in camelCase for React state and components. */
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
  userEmail?: string
  userFullName?: string
  /** From API: "active" | "closed" */
  status: 'active' | 'closed'
}

/** One conversational turn in the UI domain model. */
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

/** Patient reply and optional audio after the trainee submits a turn. */
export interface TurnResponseWithAudio {
  turn: Turn
  patientReply: string
  transcript?: string
  audioUrl?: string
  assistantAudioUrl?: string
  spikesStage?: string
}

/** Session with embedded turns for detail views. */
export interface SessionDetail extends Session {
  turns: Turn[]
}

/** Paginated session list wire response. */
export interface SessionListResponseDTO {
  sessions: SessionDTO[]
  total: number
}

/** Paginated session list for the UI. */
export interface SessionListResponse {
  sessions: Session[]
  total: number
}

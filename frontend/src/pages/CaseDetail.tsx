/**
 * Interactive case simulation: text/voice turns, SPIKES progress, session timer, end session.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { getCase } from '@/api/cases.api'
import {
  createSession,
  transcribeAudioTurn,
  submitTurn,
  submitAudioTurn,
  closeSession,
  getSession,
  fetchAssistantAudioObjectUrl,
} from '@/api/sessions.api'
import type { Case as CaseType } from '@/types/case'
import type { AudioToneAnalysis, Message } from '@/types/session'
import { parseUtcDateTime } from '@/lib/dateTime'
import { useAuthStore } from '@/store/authStore'
import { useRealtimeSession } from '@/hooks/useRealtimeSession'
import {
  evaluateVoiceCaptureForUpload,
  getPreferredRecordingMimeType,
  getRecordingFileExtension,
  isBrowserVoiceRecordingSupported,
  MIN_VOICE_ACTIVE_FRAMES,
  VOICE_ACTIVITY_RMS_THRESHOLD,
} from '@/lib/voiceMedia'
import { playAssistantAudioTrack, revokeAssistantAudioSession } from '@/lib/assistantAudioPlayback'

import { ChatBubble } from '@/components/ChatBubble'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Mic, Send, Clock, PhoneOff, ChevronDown, ChevronUp } from 'lucide-react'
import { SpikesProgressBar } from '@/components/SpikesProgressBar'

const CONVERSATION_AUTO_STOP_SILENCE_MS = 2200
const CONVERSATION_AUTO_RESUME_DELAY_MS = 350

/** Narrow axios-style error shape for user-facing messages. */
type ApiErrorShape = {
  response?: {
    data?: {
      detail?: string
      message?: string
    }
  }
}

const parseVoiceToneFromMetrics = (metricsJson?: string): AudioToneAnalysis | undefined => {
  if (!metricsJson) return undefined

  try {
    const parsed = JSON.parse(metricsJson)
    const rawTone = parsed?.voice_tone
    if (!rawTone || typeof rawTone !== 'object') return undefined

    return {
      primary: typeof rawTone.primary === 'string' ? rawTone.primary : 'neutral',
      secondary: typeof rawTone.secondary === 'string' ? rawTone.secondary : undefined,
      confidence: typeof rawTone.confidence === 'number' ? rawTone.confidence : 0,
      dimensions: {
        valence: typeof rawTone.dimensions?.valence === 'number' ? rawTone.dimensions.valence : undefined,
        arousal: typeof rawTone.dimensions?.arousal === 'number' ? rawTone.dimensions.arousal : undefined,
        paceWpm: typeof rawTone.dimensions?.pace_wpm === 'number' ? rawTone.dimensions.pace_wpm : undefined,
        volumeDb: typeof rawTone.dimensions?.volume_db === 'number' ? rawTone.dimensions.volume_db : undefined,
        pitchHz: typeof rawTone.dimensions?.pitch_hz === 'number' ? rawTone.dimensions.pitch_hz : undefined,
        jitter: typeof rawTone.dimensions?.jitter === 'number' ? rawTone.dimensions.jitter : undefined,
        shimmer: typeof rawTone.dimensions?.shimmer === 'number' ? rawTone.dimensions.shimmer : undefined,
        pausesPerMin: typeof rawTone.dimensions?.pauses_per_min === 'number' ? rawTone.dimensions.pauses_per_min : undefined,
      },
      labels: Array.isArray(rawTone.labels) ? rawTone.labels.filter((label: unknown): label is string => typeof label === 'string') : [],
      provider: typeof rawTone.provider === 'string' ? rawTone.provider : 'prosody_v1',
    }
  } catch {
    return undefined
  }
}

/**
 * Live case page: loads case + session, renders chat, briefing, voice pipeline, and close flow.
 *
 * @remarks
 * Resumes `sessionId` from query string or creates a session; manages MediaRecorder and optional TTS playback.
 *
 * @returns Full case simulation layout
 */
export const CaseDetail = () => {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [caseData, setCaseData] = useState<CaseType | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [sessionElapsed, setSessionElapsed] = useState(0)
  const [startTime, setStartTime] = useState<Date | null>(null)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [currentSpikesStage, setCurrentSpikesStage] = useState<string>('setting')
  const [error, setError] = useState<string | null>(null)
  const [closing, setClosing] = useState(false)
  const [briefingExpanded, setBriefingExpanded] = useState(false)
  type BriefingTab = 'patientBackground' | 'objectives' | 'script' | 'expectedSpikesFlow'
  const [briefingTab, setBriefingTab] = useState<BriefingTab>('patientBackground')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const createdSessionForCase = useRef<number | null>(null)
  const initializingRef = useRef(false)
  const sessionParam = searchParams.get('sessionId')
  const [isRecording, setIsRecording] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState<string | null>(null)
  const [audioResponsesEnabled, setAudioResponsesEnabled] = useState(false)
  const [conversationModeEnabled, setConversationModeEnabled] = useState(false)
  const authToken = useAuthStore((state) => state.token)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const audioMonitorFrameRef = useRef<number | null>(null)
  const voiceActivityRef = useRef({ maxRms: 0, activeFrames: 0 })
  const recordingStartedAtRef = useRef<number | null>(null)
  const activeAssistantAudioRef = useRef<HTMLAudioElement | null>(null)
  const activeAssistantAudioObjectUrlRef = useRef<string | null>(null)
  const silenceStartedAtRef = useRef<number | null>(null)
  const autoStopTriggeredRef = useRef(false)
  const conversationLoopArmedRef = useRef(false)
  const pendingConversationResumeTimeoutRef = useRef<number | null>(null)
  const requestConversationResumeRef = useRef<() => void>(() => {})

  // --- Load case and create or resume session ---
  useEffect(() => {
    /**
     * Loads case metadata and either resumes `sessionId` from the URL or creates a new session.
     */
    const initializeSession = async () => {
      if (initializingRef.current) return
      initializingRef.current = true

      if (!caseId) return

      const numericCaseId = Number(caseId)
      const resumeSessionId = sessionParam ? Number(sessionParam) : null
      const shouldResume =
        resumeSessionId !== null && !Number.isNaN(resumeSessionId)

      if (!shouldResume && createdSessionForCase.current === numericCaseId) {
        return
      }

      try {
        // Load case data
        const data = await getCase(numericCaseId)
        setCaseData(data)

        if (shouldResume) {
          const existingSession = await getSession(resumeSessionId as number)
          if (existingSession.caseId !== numericCaseId) {
            throw new Error('Session case mismatch')
          }
          setSessionId(existingSession.id)
          setCurrentSpikesStage(existingSession.currentSpikesStage || 'setting')
          const startedAt = parseUtcDateTime(existingSession.startedAt)
          if (!startedAt) {
            throw new Error('Invalid session start time')
          }
          const now = Date.now()
          const rawElapsed = Math.floor((now - startedAt.getTime()) / 1000)
          const clampedElapsed = Math.max(rawElapsed, 0)
          setSessionElapsed(clampedElapsed)
          setStartTime(new Date(now - clampedElapsed * 1000))
          const restoredMessages: Message[] = existingSession.turns.map((turn) => ({
            id: `turn-${turn.id}`,
            role: turn.role as 'user' | 'assistant',
            content: turn.text,
            timestamp: turn.timestamp,
            source:
              turn.role === 'user' &&
              (turn.audioUrl || parseVoiceToneFromMetrics(turn.metricsJson))
                ? 'audio'
                : 'text',
            assistantAudioUrl: turn.role === 'assistant' ? turn.audioUrl : undefined,
            voiceTone: turn.role === 'user' ? parseVoiceToneFromMetrics(turn.metricsJson) : undefined,
          }))
          setMessages(restoredMessages)
        } else {
          createdSessionForCase.current = numericCaseId
          try {
            const session = await createSession(numericCaseId, { forceNew: true })
            setSessionId(session.id)
            setCurrentSpikesStage(session.currentSpikesStage || 'setting')

            // Start timer
            const now = new Date()
            setStartTime(now)
            setSessionElapsed(0)

            // Always load session detail so we get turns for both new and resumed sessions
            const detail = await getSession(session.id)
            const restoredMessages: Message[] = detail.turns.map((turn) => ({
              id: `turn-${turn.id}`,
              role: turn.role as 'user' | 'assistant',
              content: turn.text,
              timestamp: turn.timestamp,
              source:
                turn.role === 'user' &&
                (turn.audioUrl || parseVoiceToneFromMetrics(turn.metricsJson))
                  ? 'audio'
                  : 'text',
              assistantAudioUrl: turn.role === 'assistant' ? turn.audioUrl : undefined,
              voiceTone: turn.role === 'user' ? parseVoiceToneFromMetrics(turn.metricsJson) : undefined,
            }))
            setMessages(restoredMessages)
          } catch (creationError) {
            createdSessionForCase.current = null
            throw creationError
          }
        }
      } catch (error) {
        console.error('Failed to initialize session:', error)
        setError('Failed to start session. Please try again.')
      } finally {
        initializingRef.current = false
        setLoading(false)
      }
    }
    initializeSession()
  }, [caseId, sessionParam])

  // --- Timer updates every second ---
  useEffect(() => {
    if (!startTime) return
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime.getTime()) / 1000)
      setSessionElapsed(elapsed)
    }, 1000)
    return () => clearInterval(timer)
  }, [startTime])

  // --- Scroll chat to latest message ---
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  // --- Message submission ---
  /**
   * Sends the current text input as a turn and appends assistant reply messages.
   *
   * @param e - Form submit from the composer
   */
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || sending || isRecording || !sessionId) return

    conversationLoopArmedRef.current = false
    const userMessageContent = inputValue
    setInputValue('')
    setSending(true)
    setError(null)
    setVoiceStatus(null)
    stopAssistantAudioPlayback()

    // Add user message to UI immediately
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userMessageContent,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])

    if (conversationModeEnabled && sendTextTurn(userMessageContent, audioResponsesEnabled)) {
      return
    }

    try {
      // Submit turn to backend and get patient response
      const response = await submitTurn(sessionId, userMessageContent, undefined, audioResponsesEnabled)

      appendAssistantMessage({
        content: response.patientReply,
        timestamp: response.turn.timestamp,
        turnId: response.turn.id,
        spikesStage: response.spikesStage,
        assistantAudioUrl: response.assistantAudioUrl,
      })
      if (response.assistantAudioUrl) {
        void playAssistantAudio(response.assistantAudioUrl)
      }
    } catch (error: unknown) {
      console.error('Failed to submit turn:', error)
      setError(getErrorMessage(error, 'Failed to send message. Please try again.'))
      
      // Add error message to chat
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your message. Please try again.',
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setSending(false)
    }
  }

  /**
   * Stops the voice activity animation frame and closes audio analysis nodes.
   */
  const stopAudioAnalysis = useCallback(() => {
    if (audioMonitorFrameRef.current !== null) {
      cancelAnimationFrame(audioMonitorFrameRef.current)
      audioMonitorFrameRef.current = null
    }

    sourceNodeRef.current?.disconnect()
    sourceNodeRef.current = null
    analyserRef.current = null

    if (audioContextRef.current) {
      void audioContextRef.current.close()
      audioContextRef.current = null
    }
  }, [])

  /**
   * Stops media tracks from the active recording stream.
   */
  const stopMediaStream = useCallback(() => {
    stopAudioAnalysis()
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
    mediaStreamRef.current = null
  }, [stopAudioAnalysis])

  /**
   * Runs an RMS-based voice activity loop to reflect mic input in the UI.
   *
   * @param stream - Captured microphone stream
   */
  const startVoiceActivityMonitoring = useCallback((stream: MediaStream) => {
    if (typeof window === 'undefined' || typeof window.AudioContext === 'undefined') {
      voiceActivityRef.current = { maxRms: 0, activeFrames: 0 }
      return
    }

    const audioContext = new window.AudioContext()
    const analyser = audioContext.createAnalyser()
    analyser.fftSize = 2048
    analyser.smoothingTimeConstant = 0.2

    const sourceNode = audioContext.createMediaStreamSource(stream)
    sourceNode.connect(analyser)

    const samples = new Uint8Array(analyser.fftSize)
    voiceActivityRef.current = { maxRms: 0, activeFrames: 0 }
    audioContextRef.current = audioContext
    analyserRef.current = analyser
    sourceNodeRef.current = sourceNode

    /**
     * Animation frame loop: computes RMS and updates voice activity counters.
     */
    const monitor = () => {
      analyser.getByteTimeDomainData(samples)

      let sumSquares = 0
      for (const sample of samples) {
        const normalized = (sample - 128) / 128
        sumSquares += normalized * normalized
      }

      const rms = Math.sqrt(sumSquares / samples.length)
      if (rms > voiceActivityRef.current.maxRms) {
        voiceActivityRef.current.maxRms = rms
      }
      if (rms >= VOICE_ACTIVITY_RMS_THRESHOLD) {
        voiceActivityRef.current.activeFrames += 1
        silenceStartedAtRef.current = null
      } else if (
        conversationModeEnabled &&
        !autoStopTriggeredRef.current &&
        voiceActivityRef.current.activeFrames >= MIN_VOICE_ACTIVE_FRAMES &&
        mediaRecorderRef.current?.state === 'recording'
      ) {
        const now = Date.now()
        silenceStartedAtRef.current ??= now

        if (now - silenceStartedAtRef.current >= CONVERSATION_AUTO_STOP_SILENCE_MS) {
          autoStopTriggeredRef.current = true
          setVoiceStatus('Speech paused. Preparing your message...')
          mediaRecorderRef.current.stop()
          return
        }
      }

      audioMonitorFrameRef.current = requestAnimationFrame(monitor)
    }

    monitor()
  }, [conversationModeEnabled])

  useEffect(() => {
    return () => {
      if (pendingConversationResumeTimeoutRef.current !== null) {
        window.clearTimeout(pendingConversationResumeTimeoutRef.current)
        pendingConversationResumeTimeoutRef.current = null
      }
      revokeAssistantAudioSession(activeAssistantAudioRef, activeAssistantAudioObjectUrlRef)
      mediaRecorderRef.current?.stream.getTracks().forEach((track) => track.stop())
      mediaRecorderRef.current = null
      stopMediaStream()
      audioChunksRef.current = []
    }
  }, [stopMediaStream])

  const stopAssistantAudioPlayback = useCallback(() => {
    if (pendingConversationResumeTimeoutRef.current !== null) {
      window.clearTimeout(pendingConversationResumeTimeoutRef.current)
      pendingConversationResumeTimeoutRef.current = null
    }
    activeAssistantAudioRef.current?.pause()
    activeAssistantAudioRef.current = null
    if (activeAssistantAudioObjectUrlRef.current) {
      URL.revokeObjectURL(activeAssistantAudioObjectUrlRef.current)
      activeAssistantAudioObjectUrlRef.current = null
    }
  }, [])

  /**
   * Fetches assistant audio as a blob URL and plays it, revoking previous object URLs.
   *
   * @param audioUrl - URL returned by the API for TTS
   */
  const playAssistantAudio = useCallback(async (audioUrl: string) => {
    try {
      await playAssistantAudioTrack(audioUrl, {
        activeAudioRef: activeAssistantAudioRef,
        activeObjectUrlRef: activeAssistantAudioObjectUrlRef,
        fetchObjectUrl: fetchAssistantAudioObjectUrl,
        onPlaybackEnded: () => requestConversationResumeRef.current(),
      })
    } catch (playbackError) {
      console.warn('Assistant audio playback failed:', playbackError)
      requestConversationResumeRef.current()
    }
  }, [])

  /**
   * Merges updates into an existing chat message by id.
   *
   * @param messageId - Client message id
   * @param updates - Partial message fields
   */
  const updateMessage = (messageId: string, updates: Partial<Message>) => {
    setMessages((prev) =>
      prev.map((message) => (message.id === messageId ? { ...message, ...updates } : message))
    )
  }

  const appendAssistantMessage = useCallback(
    ({
      content,
      timestamp,
      turnId,
      spikesStage,
      assistantAudioUrl,
    }: {
      content: string
      timestamp?: string
      turnId?: number
      spikesStage?: string
      assistantAudioUrl?: string
    }) => {
      if (spikesStage) {
        setCurrentSpikesStage(spikesStage)
      }

      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${turnId ?? Date.now()}`,
          role: 'assistant',
          content,
          timestamp: timestamp ?? new Date().toISOString(),
          source: 'text',
          status: 'sent',
          assistantAudioUrl,
        },
      ])
    },
    []
  )

  const handleConversationError = useCallback((message: string) => {
    setSending(false)
    setError(message)
    setMessages((prev) => [
      ...prev,
      {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: message,
        timestamp: new Date().toISOString(),
      },
    ])
  }, [])

  const handleConversationAssistantMessage = useCallback(
    ({
      content,
      turnId,
      spikesStage,
      assistantAudioUrl,
    }: {
      content: string
      turnId?: number
      spikesStage?: string
      assistantAudioUrl?: string
    }) => {
      setSending(false)
      appendAssistantMessage({
        content,
        turnId,
        spikesStage,
        assistantAudioUrl,
      })
      if (assistantAudioUrl) {
        void playAssistantAudio(assistantAudioUrl)
      } else {
        requestConversationResumeRef.current()
      }
    },
    [appendAssistantMessage, playAssistantAudio]
  )

  const handleConversationStageUpdate = useCallback((stage: string) => {
    setCurrentSpikesStage(stage)
  }, [])

  const {
    connectionStatus: conversationConnectionStatus,
    isConnected: isConversationConnected,
    isPatientResponding: isConversationPatientResponding,
    sendTextTurn,
  } = useRealtimeSession({
    enabled: conversationModeEnabled,
    sessionId,
    token: authToken,
    onAssistantMessage: handleConversationAssistantMessage,
    onStageUpdate: handleConversationStageUpdate,
    onError: handleConversationError,
  })

  /**
   * Extracts API error detail/message for toast-style display.
   *
   * @param error - Caught error
   * @param fallback - Default message
   * @returns User-facing string
   */
  const getErrorMessage = (error: unknown, fallback: string) => {
    const apiError = error as ApiErrorShape
    return apiError.response?.data?.message || apiError.response?.data?.detail || fallback
  }

  /**
   * Transcribes audio then submits the text turn, updating the pending message in place.
   *
   * @param audioFile - Recorded audio blob as a file
   * @param pendingMessageId - Optimistic message id to replace content on success
   */
  const uploadRecordedAudio = async (audioFile: File, pendingMessageId: string) => {
    if (!sessionId) return

    setSending(true)
    setVoiceStatus(
      conversationModeEnabled
        ? 'Sending voice turn in conversation mode...'
        : 'Transcribing voice message...'
    )

    try {
      if (conversationModeEnabled) {
        const response = await submitAudioTurn(sessionId, audioFile, audioResponsesEnabled)

        updateMessage(pendingMessageId, {
          content: response.transcript || 'Voice message sent.',
          status: 'sent',
          voiceTone: response.audioTone,
        })

        appendAssistantMessage({
          content: response.patientReply,
          timestamp: response.turn.timestamp,
          turnId: response.turn.id,
          spikesStage: response.spikesStage,
          assistantAudioUrl: response.assistantAudioUrl,
        })
        if (response.assistantAudioUrl) {
          void playAssistantAudio(response.assistantAudioUrl)
        } else {
          requestConversationResumeRef.current()
        }
        return
      }

      const transcription = await transcribeAudioTurn(sessionId, audioFile)

      updateMessage(pendingMessageId, {
        content: transcription.transcript || 'Voice message sent.',
        status: 'sent',
        voiceTone: transcription.audioTone,
      })

      setVoiceStatus(null)

      const response = await submitTurn(
        sessionId,
        transcription.transcript,
        undefined,
        audioResponsesEnabled,
        transcription.audioTone,
      )

      appendAssistantMessage({
        content: response.patientReply,
        timestamp: response.turn.timestamp,
        turnId: response.turn.id,
        spikesStage: response.spikesStage,
        assistantAudioUrl: response.assistantAudioUrl,
      })
      if (response.assistantAudioUrl) {
        void playAssistantAudio(response.assistantAudioUrl)
      } else {
        requestConversationResumeRef.current()
      }
    } catch (uploadError: unknown) {
      console.error('Failed to submit audio turn:', uploadError)
      setError(getErrorMessage(uploadError, 'Failed to process voice input. Please try again.'))
      updateMessage(pendingMessageId, {
        content: 'Voice message failed. Please try again.',
        status: 'error',
      })
    } finally {
      setSending(false)
      setVoiceStatus(null)
    }
  }

  /**
   * Starts mic capture, voice activity monitoring, and MediaRecorder; on stop, uploads audio.
   */
  const startVoiceRecording = async () => {
    if (!sessionId || sending || closing) return

    if (!isBrowserVoiceRecordingSupported()) {
      setError('Voice input is not supported in this browser.')
      return
    }

    setError(null)
    setVoiceStatus('Requesting microphone access...')
    stopAssistantAudioPlayback()
    silenceStartedAtRef.current = null
    autoStopTriggeredRef.current = false
    if (conversationModeEnabled) {
      conversationLoopArmedRef.current = true
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = getPreferredRecordingMimeType((m) => MediaRecorder.isTypeSupported(m))
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)

      audioChunksRef.current = []
      recordingStartedAtRef.current = Date.now()
      mediaRecorderRef.current = recorder
      mediaStreamRef.current = stream
      startVoiceActivityMonitoring(stream)

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      recorder.onerror = () => {
        setError('Microphone recording failed. Please try again.')
        setIsRecording(false)
        setVoiceStatus(null)
        stopMediaStream()
      }

      recorder.onstop = () => {
        setIsRecording(false)

        const { activeFrames, maxRms } = voiceActivityRef.current
        const recordingDurationMs = recordingStartedAtRef.current
          ? Date.now() - recordingStartedAtRef.current
          : 0
        recordingStartedAtRef.current = null
        silenceStartedAtRef.current = null
        autoStopTriggeredRef.current = false
        const recordedMimeType = recorder.mimeType || audioChunksRef.current[0]?.type || 'audio/webm'
        const audioBlob = new Blob(audioChunksRef.current, { type: recordedMimeType })
        audioChunksRef.current = []
        stopMediaStream()

        const captureDecision = evaluateVoiceCaptureForUpload({
          blobByteSize: audioBlob.size,
          maxRms,
          activeFrames,
          recordingDurationMs,
        })

        if (!captureDecision.upload) {
          setVoiceStatus(null)
          if (captureDecision.reason === 'empty_blob') {
            setError('No audio was captured. Please try again.')
          } else {
            setError('No speech was detected. Please try again and speak before stopping the microphone.')
          }
          return
        }

        const pendingMessageId = `audio-${Date.now()}`
        const pendingMessage: Message = {
          id: pendingMessageId,
          role: 'user',
          content: conversationModeEnabled ? 'Processing voice message...' : 'Transcribing voice message...',
          timestamp: new Date().toISOString(),
          source: 'audio',
          status: 'pending',
        }
        setMessages((prev) => [...prev, pendingMessage])

        const extension = getRecordingFileExtension(recordedMimeType)
        const audioFile = new File([audioBlob], `voice-message-${Date.now()}.${extension}`, {
          type: recordedMimeType,
        })
        void uploadRecordedAudio(audioFile, pendingMessageId)
      }

      recorder.start()
      setIsRecording(true)
      setVoiceStatus(
        conversationModeEnabled
          ? 'Listening... I will stop when you pause.'
          : 'Listening... Start speaking, then tap the microphone again to stop.'
      )
    } catch (recordError) {
      console.error('Failed to start recording:', recordError)
      setError('Microphone access was denied or is unavailable.')
      recordingStartedAtRef.current = null
      setVoiceStatus(null)
      stopMediaStream()
    }
  }

  requestConversationResumeRef.current = () => {
    if (!conversationLoopArmedRef.current || !conversationModeEnabled || closing || !sessionId) {
      return
    }

    if (pendingConversationResumeTimeoutRef.current !== null) {
      window.clearTimeout(pendingConversationResumeTimeoutRef.current)
    }

    pendingConversationResumeTimeoutRef.current = window.setTimeout(() => {
      pendingConversationResumeTimeoutRef.current = null

      if (
        !conversationLoopArmedRef.current ||
        !conversationModeEnabled ||
        closing ||
        mediaRecorderRef.current?.state === 'recording'
      ) {
        return
      }

      void startVoiceRecording()
    }, CONVERSATION_AUTO_RESUME_DELAY_MS)
  }

  /**
   * Toggles recording: starts when idle, stops and uploads when active.
   */
  const handleVoiceInput = () => {
    if (isRecording) {
      autoStopTriggeredRef.current = true
      mediaRecorderRef.current?.stop()
      setVoiceStatus('Preparing voice message...')
      return
    }

    void startVoiceRecording()
  }

  useEffect(() => {
    if (!conversationModeEnabled) {
      conversationLoopArmedRef.current = false
      if (pendingConversationResumeTimeoutRef.current !== null) {
        window.clearTimeout(pendingConversationResumeTimeoutRef.current)
        pendingConversationResumeTimeoutRef.current = null
      }
      return
    }

    setAudioResponsesEnabled(true)
  }, [conversationModeEnabled])

  /**
   * Closes the session server-side and navigates to feedback when successful.
   */
  const handleEndSession = async () => {
    if (!sessionId) return
    setClosing(true)
    setError(null)

    try {
      await closeSession(sessionId)
      navigate(`/feedback/${sessionId}`)
    } catch (err: unknown) {
      console.error('Failed to close session:', err)
      setError(getErrorMessage(err, 'Failed to end session. Please try again.'))
      setClosing(false)
    }
  }

  /**
   * Formats elapsed session seconds as `m:ss`.
   *
   * @param seconds - Elapsed seconds
   * @returns Timer label
   */
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const showVoiceIndicator = isRecording
  const showPatientRespondingIndicator =
    (sending && !voiceStatus) || isConversationPatientResponding
  const listeningBarHeights = ['38%', '72%', '54%', '80%', '46%']
  const conversationStatusLabel = !conversationModeEnabled
    ? 'Off'
    : conversationConnectionStatus === 'connected'
      ? 'Connected'
      : conversationConnectionStatus === 'connecting'
        ? 'Connecting...'
        : conversationConnectionStatus === 'error'
          ? 'Connection error'
          : 'Disconnected'

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-500">Loading case...</div>
      </div>
    )
  }

  if (!caseData) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-500">Case not found</div>
      </div>
    )
  }

  const difficultyLabel = caseData.difficultyLevel
    ? `${caseData.difficultyLevel.charAt(0).toUpperCase()}${caseData.difficultyLevel.slice(1)}`
    : 'No difficulty'

  return (
    <div className="flex h-screen flex-col">
      <style>
        {`
          @keyframes listening-wave {
            0%, 100% { transform: scaleY(0.45); opacity: 0.65; }
            50% { transform: scaleY(1); opacity: 1; }
          }
        `}
      </style>
      <Navbar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 overflow-y-auto bg-slate-50 md:ml-64 xl:overflow-hidden">
          <div className="flex min-h-full flex-col px-4 py-4 sm:px-6 lg:px-8 xl:h-full">
            <div className="mb-4 rounded-3xl border border-slate-200 bg-white px-4 py-4 shadow-sm sm:px-5">
              <nav className="text-sm text-gray-500">
                <span>Dashboard</span> / <span className="text-gray-900">Case</span>
              </nav>

              <div className="mt-3 flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="space-y-3">
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight text-gray-900">{caseData.title}</h1>
                    {caseData.description && (
                      <p className="mt-1 max-w-3xl text-sm text-gray-600">{caseData.description}</p>
                    )}
                  </div>

                </div>

                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleEndSession}
                  disabled={closing}
                  className="h-11 shrink-0 rounded-xl px-4 text-sm font-semibold"
                >
                  <PhoneOff className="mr-2 h-4 w-4" />
                  {closing ? 'Generating Feedback...' : 'End Session'}
                </Button>
              </div>
            </div>

            <div className="grid gap-4 xl:min-h-0 xl:flex-1 xl:grid-cols-[minmax(0,1.55fr)_24.5rem]">
              <section className="flex min-h-[520px] flex-col overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm xl:min-h-0">
                <div className="flex-1 overflow-y-auto bg-gradient-to-b from-slate-50 via-white to-slate-50 px-4 py-5 sm:px-6">
                  <div className="mx-auto flex w-full max-w-5xl flex-col gap-4">
                    {messages.length === 0 && !sending && (
                      <div className="rounded-3xl border border-dashed border-slate-200 bg-white/80 px-6 py-12 text-center text-gray-500 shadow-sm">
                        <p className="text-lg font-semibold text-gray-800">Start the conversation</p>
                        <p className="mt-2 text-sm">
                          Begin by introducing yourself and follow the SPIKES framework while you respond.
                        </p>
                      </div>
                    )}
                    {messages.map((message) => (
                      <ChatBubble key={message.id} message={message} onReplayAudio={playAssistantAudio} />
                    ))}
                    {showPatientRespondingIndicator && (
                      <div className="inline-flex w-fit items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-sm text-gray-500">
                        <div className="h-2 w-2 animate-pulse rounded-full bg-gray-400" />
                        Patient is responding...
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                </div>

                <div className="border-t border-slate-200 bg-white px-4 py-4 sm:px-5">
                  <form onSubmit={handleSubmit} className="space-y-3">
                    {error && (
                      <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {error}
                      </div>
                    )}
                    <div
                      className={`rounded-2xl p-2 shadow-inner transition-colors duration-200 ${
                        showVoiceIndicator
                          ? 'border border-apex-200 bg-apex-50'
                          : 'border border-slate-200 bg-slate-50/80'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {showVoiceIndicator ? (
                          <div className="flex h-12 flex-1 items-center gap-3 rounded-xl px-3 text-apex-900">
                            <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-apex-500" />
                            <div className="min-w-0">
                              <div className="font-medium">Listening</div>
                              <div className="truncate text-xs text-apex-700">
                                Tap the microphone again when you are done speaking.
                              </div>
                            </div>
                          </div>
                        ) : (
                          <Input
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            placeholder="Type your message following the SPIKES framework..."
                            disabled={sending || isRecording}
                            className="h-12 flex-1 border-0 bg-transparent px-3 shadow-none focus-visible:ring-0"
                          />
                        )}
                        {showVoiceIndicator && (
                          <div className="mr-2 flex h-8 w-16 shrink-0 items-end justify-end gap-1">
                            {listeningBarHeights.map((height, index) => (
                              <span
                                key={`voice-bar-${index}`}
                                className="w-1.5 origin-bottom rounded-full bg-apex-500"
                                style={{
                                  height,
                                  animation: `listening-wave 0.9s ease-in-out ${index * 0.12}s infinite`,
                                }}
                              />
                            ))}
                          </div>
                        )}
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={handleVoiceInput}
                          disabled={sending || closing || !sessionId}
                          className={isRecording ? 'h-12 w-12 shrink-0 rounded-2xl border-red-500 bg-red-50 text-red-600 shadow-[0_0_0_4px_rgba(239,68,68,0.12)]' : 'h-12 w-12 shrink-0 rounded-2xl border-slate-200 bg-white'}
                          title={isRecording ? 'Stop recording' : 'Start voice input'}
                        >
                          <Mic className="h-5 w-5" />
                        </Button>
                        <Button
                          type="submit"
                          size="icon"
                          disabled={sending || closing || isRecording || !inputValue.trim() || !sessionId}
                          className="h-12 w-12 shrink-0 rounded-2xl"
                        >
                          <Send className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </form>
                </div>
              </section>

              <aside className="flex flex-col gap-4 xl:h-full xl:min-h-0 xl:overflow-y-auto xl:pr-1">
                <Card className="shrink-0 rounded-[28px] border-slate-200 shadow-sm">
                  <CardHeader className="space-y-1 border-b border-slate-100 pb-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <CardTitle className="text-base">Case Briefing</CardTitle>
                        <p className="text-sm text-gray-500">
                          Reference the brief without letting it compete with the conversation.
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-slate-700 hover:bg-slate-50"
                        onClick={() => setBriefingExpanded((expanded) => !expanded)}
                      >
                        {briefingExpanded ? (
                          <>
                            <ChevronUp className="mr-2 h-4 w-4" />
                            Hide
                          </>
                        ) : (
                          <>
                            <ChevronDown className="mr-2 h-4 w-4" />
                            Show
                          </>
                        )}
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="min-w-0 space-y-4 px-6 pb-6 pt-5">
                    {!briefingExpanded ? (
                      <div className="rounded-2xl bg-slate-50 px-4 py-4">
                        <p className="text-[15px] leading-7 text-gray-600">
                          {caseData.patientBackground?.trim() || caseData.description || 'No briefing preview.'}
                        </p>
                      </div>
                    ) : (
                      <>
                        <div className="min-w-0 flex flex-wrap gap-2 border-b border-gray-200 pb-4">
                          {caseData.patientBackground != null && (
                            <button
                              type="button"
                              onClick={() => setBriefingTab('patientBackground')}
                              className={`rounded-full px-3.5 py-2 text-xs font-medium ${
                                briefingTab === 'patientBackground'
                                  ? 'bg-apex-100 text-apex-900'
                                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                              }`}
                            >
                              Patient background
                            </button>
                          )}
                          {caseData.objectives != null && (
                            <button
                              type="button"
                              onClick={() => setBriefingTab('objectives')}
                              className={`rounded-full px-3.5 py-2 text-xs font-medium ${
                                briefingTab === 'objectives'
                                  ? 'bg-apex-100 text-apex-900'
                                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                              }`}
                            >
                              Objectives
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => setBriefingTab('script')}
                            className={`rounded-full px-3.5 py-2 text-xs font-medium ${
                              briefingTab === 'script'
                                ? 'bg-apex-100 text-apex-900'
                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }`}
                          >
                            Script
                          </button>
                          {caseData.expectedSpikesFlow != null && (
                            <button
                              type="button"
                              onClick={() => setBriefingTab('expectedSpikesFlow')}
                              className={`rounded-full px-3.5 py-2 text-xs font-medium ${
                                briefingTab === 'expectedSpikesFlow'
                                  ? 'bg-apex-100 text-apex-900'
                                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                              }`}
                            >
                              Expected SPIKES flow
                            </button>
                          )}
                        </div>
                        <div className="min-w-0 rounded-2xl bg-slate-50 px-4 py-4">
                          {briefingTab === 'patientBackground' && (
                            <pre className="max-w-full whitespace-pre-wrap break-words text-[15px] leading-7 text-gray-800">
                              {caseData.patientBackground || '—'}
                            </pre>
                          )}
                          {briefingTab === 'objectives' && (
                            <pre className="max-w-full whitespace-pre-wrap break-words text-[15px] leading-7 text-gray-800">
                              {caseData.objectives ?? '—'}
                            </pre>
                          )}
                          {briefingTab === 'script' && (
                            <pre className="max-w-full whitespace-pre-wrap break-words text-[15px] leading-7 text-gray-800">
                              {caseData.script}
                            </pre>
                          )}
                          {briefingTab === 'expectedSpikesFlow' && (
                            <pre className="max-w-full whitespace-pre-wrap break-words text-[15px] leading-7 text-gray-800">
                              {caseData.expectedSpikesFlow ?? '—'}
                            </pre>
                          )}
                        </div>
                      </>
                    )}
                  </CardContent>
                </Card>

                <Card className="shrink-0 rounded-[28px] border-slate-200 shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Session Overview</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-5 px-5 pb-5 pt-0">
                    <div>
                      <SpikesProgressBar currentStage={currentSpikesStage} />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div
                        className={`rounded-2xl border border-slate-200 bg-white p-4 ${
                          sessionId ? '' : 'col-span-2'
                        }`}
                      >
                        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-apex-50 text-apex-700">
                            <Clock className="h-3.5 w-3.5" />
                          </span>
                          Session time
                        </div>
                        <div className="mt-2 text-xl font-semibold text-slate-900">
                          {formatTime(sessionElapsed)}
                        </div>
                      </div>
                      {sessionId && (
                        <div className="rounded-2xl border border-slate-200 bg-white p-4">
                          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            Session ID
                          </div>
                          <div className="mt-2 text-sm font-semibold text-slate-900">{sessionId}</div>
                        </div>
                      )}
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                          Level
                        </div>
                        <div className="mt-2 text-sm font-semibold text-slate-900">{difficultyLabel}</div>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-white p-4">
                        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                          Type
                        </div>
                        <div className="mt-2 text-sm font-semibold text-slate-900">
                          {caseData.category ?? 'No category'}
                        </div>
                      </div>
                      <div className="col-span-2 rounded-2xl border border-slate-200 bg-white p-4">
                        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                          Audio responses
                        </div>
                        <label className="mt-2 inline-flex items-center gap-2 text-sm text-slate-900">
                          <input
                            type="checkbox"
                            checked={audioResponsesEnabled}
                            onChange={(e) => setAudioResponsesEnabled(e.target.checked)}
                            disabled={sending || closing}
                            className="h-4 w-4 rounded border-gray-300 text-apex-600 focus:ring-apex-500"
                          />
                          <span>Enable spoken replies</span>
                        </label>
                      </div>
                      <div className="col-span-2 rounded-2xl border border-slate-200 bg-white p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                              Conversation mode
                            </div>
                            <p className="mt-2 text-sm text-slate-900">
                              Turn on the live conversation channel while keeping the default flow available.
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              Status: {conversationStatusLabel}
                              {conversationModeEnabled && isConversationConnected ? ' • Live' : ''}
                            </p>
                          </div>
                          <label className="inline-flex items-center gap-2 text-sm text-slate-900">
                            <input
                              type="checkbox"
                              checked={conversationModeEnabled}
                              onChange={(e) => {
                                const enabled = e.target.checked
                                setConversationModeEnabled(enabled)
                                if (enabled) {
                                  setAudioResponsesEnabled(true)
                                }
                              }}
                              disabled={sending || closing || isRecording || !sessionId}
                              className="h-4 w-4 rounded border-gray-300 text-apex-600 focus:ring-apex-500"
                            />
                            <span>Enable</span>
                          </label>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </aside>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

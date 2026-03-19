import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { getCase } from '@/api/cases.api'
import { createSession, transcribeAudioTurn, submitTurn, closeSession, getSession } from '@/api/sessions.api'
import type { Case as CaseType } from '@/types/case'
import type { Message } from '@/types/session'

import { ChatBubble } from '@/components/ChatBubble'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Mic, Send, Clock, PhoneOff, ChevronDown, ChevronUp } from 'lucide-react'
import { SpikesProgressBar } from '@/components/SpikesProgressBar'

const audioExtensionByMimeType: Record<string, string> = {
  'audio/webm;codecs=opus': 'webm',
  'audio/webm': 'webm',
  'audio/ogg;codecs=opus': 'ogg',
  'audio/ogg': 'ogg',
  'audio/mp4': 'm4a',
  'audio/x-m4a': 'm4a',
  'audio/mpeg': 'mp3',
  'audio/mp3': 'mp3',
  'audio/wav': 'wav',
  'audio/x-wav': 'wav',
}

const preferredMimeTypes = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/ogg',
  'audio/mp4',
]

const VOICE_ACTIVITY_RMS_THRESHOLD = 0.02
const MIN_VOICE_ACTIVE_FRAMES = 5

type ApiErrorShape = {
  response?: {
    data?: {
      detail?: string
      message?: string
    }
  }
}

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
  const createdSessionForCase = useRef<number | null>(null)
  const initializingRef = useRef(false)
  const sessionParam = searchParams.get('sessionId')
  const [closing, setClosing] = useState(false)
  const [briefingExpanded, setBriefingExpanded] = useState(false)
  type BriefingTab = 'patientBackground' | 'objectives' | 'script' | 'expectedSpikesFlow'
  const [briefingTab, setBriefingTab] = useState<BriefingTab>('patientBackground')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState<string | null>(null)
  const [audioResponsesEnabled, setAudioResponsesEnabled] = useState(false)

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

  // --- Load case and create session ---
  useEffect(() => {
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
          const startedAt = new Date(existingSession.startedAt)
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
            source: turn.role === 'user' && turn.audioUrl ? 'audio' : 'text',
            assistantAudioUrl: turn.role === 'assistant' ? turn.audioUrl : undefined,
          }))
          setMessages(restoredMessages)
        } else {
          createdSessionForCase.current = numericCaseId
          try {
            const session = await createSession(numericCaseId)
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
              source: turn.role === 'user' && turn.audioUrl ? 'audio' : 'text',
              assistantAudioUrl: turn.role === 'assistant' ? turn.audioUrl : undefined,
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
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || sending || isRecording || !sessionId) return

    const userMessageContent = inputValue
    setInputValue('')
    setSending(true)
    setError(null)
    setVoiceStatus(null)

    // Add user message to UI immediately
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userMessageContent,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])

    try {
      // Submit turn to backend and get patient response
      const response = await submitTurn(sessionId, userMessageContent, undefined, audioResponsesEnabled)
      
      // Update SPIKES stage if changed
      if (response.spikesStage) {
        setCurrentSpikesStage(response.spikesStage)
      }

      // Add assistant (patient) response to UI
      const assistantMessage: Message = {
        id: `assistant-${response.turn.id}`,
        role: 'assistant',
        content: response.patientReply,
        timestamp: response.turn.timestamp,
        source: 'text',
        status: 'sent',
        assistantAudioUrl: response.assistantAudioUrl,
      }
      setMessages((prev) => [...prev, assistantMessage])
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

  const stopMediaStream = useCallback(() => {
    stopAudioAnalysis()
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
    mediaStreamRef.current = null
  }, [stopAudioAnalysis])

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
      }

      audioMonitorFrameRef.current = requestAnimationFrame(monitor)
    }

    monitor()
  }, [])

  useEffect(() => {
    return () => {
      activeAssistantAudioRef.current?.pause()
      activeAssistantAudioRef.current = null
      mediaRecorderRef.current?.stream.getTracks().forEach((track) => track.stop())
      mediaRecorderRef.current = null
      stopMediaStream()
      audioChunksRef.current = []
    }
  }, [stopMediaStream])

  const playAssistantAudio = useCallback(async (audioUrl: string) => {
    try {
      activeAssistantAudioRef.current?.pause()

      const audio = new Audio(audioUrl)
      activeAssistantAudioRef.current = audio
      audio.onended = () => {
        if (activeAssistantAudioRef.current === audio) {
          activeAssistantAudioRef.current = null
        }
      }
      await audio.play()
    } catch (playbackError) {
      console.warn('Assistant audio playback failed:', playbackError)
    }
  }, [])

  const updateMessage = (messageId: string, updates: Partial<Message>) => {
    setMessages((prev) =>
      prev.map((message) => (message.id === messageId ? { ...message, ...updates } : message))
    )
  }

  const getPreferredAudioMimeType = () => {
    if (typeof MediaRecorder === 'undefined') return ''

    return preferredMimeTypes.find((mimeType) => MediaRecorder.isTypeSupported(mimeType)) ?? ''
  }

  const getAudioExtension = (mimeType: string) => {
    return audioExtensionByMimeType[mimeType.toLowerCase()] ?? 'webm'
  }

  const getErrorMessage = (error: unknown, fallback: string) => {
    const apiError = error as ApiErrorShape
    return apiError.response?.data?.message || apiError.response?.data?.detail || fallback
  }

  const uploadRecordedAudio = async (audioFile: File, pendingMessageId: string) => {
    if (!sessionId) return

    setSending(true)
    setVoiceStatus('Transcribing voice message...')

    try {
      const transcription = await transcribeAudioTurn(sessionId, audioFile)

      updateMessage(pendingMessageId, {
        content: transcription.transcript || 'Voice message sent.',
        status: 'sent',
      })

      setVoiceStatus(null)

      const response = await submitTurn(
        sessionId,
        transcription.transcript,
        undefined,
        audioResponsesEnabled,
      )

      if (response.spikesStage) {
        setCurrentSpikesStage(response.spikesStage)
      }

      const assistantMessage: Message = {
        id: `assistant-${response.turn.id}`,
        role: 'assistant',
        content: response.patientReply,
        timestamp: response.turn.timestamp,
        source: 'text',
        status: 'sent',
        assistantAudioUrl: response.assistantAudioUrl,
      }
      setMessages((prev) => [...prev, assistantMessage])
      if (response.assistantAudioUrl) {
        void playAssistantAudio(response.assistantAudioUrl)
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

  const startVoiceRecording = async () => {
    if (!sessionId || sending || closing) return

    if (
      typeof navigator === 'undefined' ||
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === 'undefined'
    ) {
      setError('Voice input is not supported in this browser.')
      return
    }

    setError(null)
    setVoiceStatus('Requesting microphone access...')

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = getPreferredAudioMimeType()
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
        const recordedMimeType = recorder.mimeType || audioChunksRef.current[0]?.type || 'audio/webm'
        const audioBlob = new Blob(audioChunksRef.current, { type: recordedMimeType })
        audioChunksRef.current = []
        stopMediaStream()

        if (audioBlob.size === 0) {
          setVoiceStatus(null)
          setError('No audio was captured. Please try again.')
          return
        }

        const detectedSpeech =
          maxRms >= VOICE_ACTIVITY_RMS_THRESHOLD &&
          activeFrames >= MIN_VOICE_ACTIVE_FRAMES &&
          recordingDurationMs > 0

        if (!detectedSpeech) {
          setVoiceStatus(null)
          setError('No speech was detected. Please try again and speak before stopping the microphone.')
          return
        }

        const pendingMessageId = `audio-${Date.now()}`
        const pendingMessage: Message = {
          id: pendingMessageId,
          role: 'user',
          content: 'Transcribing voice message...',
          timestamp: new Date().toISOString(),
          source: 'audio',
          status: 'pending',
        }
        setMessages((prev) => [...prev, pendingMessage])

        const extension = getAudioExtension(recordedMimeType)
        const audioFile = new File([audioBlob], `voice-message-${Date.now()}.${extension}`, {
          type: recordedMimeType,
        })
        void uploadRecordedAudio(audioFile, pendingMessageId)
      }

      recorder.start()
      setIsRecording(true)
      setVoiceStatus('Listening... Start speaking, then tap the microphone again to stop.')
    } catch (recordError) {
      console.error('Failed to start recording:', recordError)
      setError('Microphone access was denied or is unavailable.')
      recordingStartedAtRef.current = null
      setVoiceStatus(null)
      stopMediaStream()
    }
  }

  const handleVoiceInput = () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop()
      setVoiceStatus('Preparing voice message...')
      return
    }

    void startVoiceRecording()
  }

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

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const showVoiceIndicator = isRecording
  const showPatientRespondingIndicator =
    sending && !voiceStatus
  const listeningBarHeights = ['38%', '72%', '54%', '80%', '46%']

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

  return (
    <div className="h-screen flex flex-col">
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
        <main className="flex-1 overflow-y-auto md:ml-64 flex flex-col">
          {/* Header */}
          <div className="border-b bg-white px-4 py-4 sm:px-6 lg:px-8">
            <nav className="mb-3 text-sm text-gray-500">
              <span>Dashboard</span> / <span className="text-gray-900">Case Detail</span>
            </nav>

            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{caseData.title}</h1>
                {caseData.description && (
                  <p className="mt-1 text-sm text-gray-600">{caseData.description}</p>
                )}
              </div>

              <Button
                variant="destructive"
                size="sm"
                onClick={handleEndSession}
                disabled={closing}
                className="flex items-center gap-2"
              >
                <PhoneOff className="h-4 w-4" />
                {closing ? 'Generating Feedback...' : 'End Session'}
              </Button>
            </div>

            {/* Timer + metadata cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card className="bg-green-50 border-green-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Session Timer
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 text-green-700 font-semibold text-lg">
                  {formatTime(sessionElapsed)}
                </CardContent>
              </Card>

              <Card className="bg-blue-50 border-blue-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Difficulty</CardTitle>
                </CardHeader>
                <CardContent className="pt-0 text-blue-700 font-semibold">
                  {caseData.difficultyLevel ?? '—'}
                </CardContent>
              </Card>

              <Card className="bg-purple-50 border-purple-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Category</CardTitle>
                </CardHeader>
                <CardContent className="pt-0 text-purple-700 font-semibold">
                  {caseData.category ?? '—'}
                </CardContent>
              </Card>

              <Card className="bg-orange-50 border-orange-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">SPIKES</CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <SpikesProgressBar currentStage={currentSpikesStage} />
                </CardContent>
              </Card>
            </div>

            <div className="mt-4">
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium">Case Briefing</CardTitle>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="bg-transparent border border-[#E5E7EB] text-[#374151] hover:bg-[#F9FAFB] outline-none focus:outline-none focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-offset-0"
                      onClick={() => setBriefingExpanded((expanded) => !expanded)}
                    >
                      {briefingExpanded ? (
                        <>
                          <ChevronUp className="mr-1 h-4 w-4" />
                          Hide briefing
                        </>
                      ) : (
                        <>
                          <ChevronDown className="mr-1 h-4 w-4" />
                          View full briefing
                        </>
                      )}
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  {!briefingExpanded ? (
                    <p className="line-clamp-2 text-sm text-gray-600">
                      {caseData.patientBackground?.trim() || caseData.description || 'No briefing preview.'}
                    </p>
                  ) : (
                    <>
                      <div className="mb-3 flex flex-wrap gap-1 border-b border-gray-200 pb-2">
                        {caseData.patientBackground != null && (
                          <button
                            type="button"
                            onClick={() => setBriefingTab('patientBackground')}
                            className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                              briefingTab === 'patientBackground'
                                ? 'bg-blue-100 text-blue-800'
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
                            className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                              briefingTab === 'objectives'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }`}
                          >
                            Objectives
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => setBriefingTab('script')}
                          className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                            briefingTab === 'script'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                          }`}
                        >
                          Script
                        </button>
                        {caseData.expectedSpikesFlow != null && (
                          <button
                            type="button"
                            onClick={() => setBriefingTab('expectedSpikesFlow')}
                            className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                              briefingTab === 'expectedSpikesFlow'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }`}
                          >
                            Expected SPIKES flow
                          </button>
                        )}
                      </div>
                      <div className="max-h-64 min-h-[120px] overflow-y-auto">
                        {briefingTab === 'patientBackground' && (
                          <pre className="whitespace-pre-wrap text-sm text-gray-800">
                            {caseData.patientBackground || '—'}
                          </pre>
                        )}
                        {briefingTab === 'objectives' && (
                          <pre className="whitespace-pre-wrap text-sm text-gray-800">
                            {caseData.objectives ?? '—'}
                          </pre>
                        )}
                        {briefingTab === 'script' && (
                          <pre className="whitespace-pre-wrap text-sm text-gray-800">
                            {caseData.script}
                          </pre>
                        )}
                        {briefingTab === 'expectedSpikesFlow' && (
                          <pre className="whitespace-pre-wrap text-sm text-gray-800">
                            {caseData.expectedSpikesFlow ?? '—'}
                          </pre>
                        )}
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
          {/* Chat area */}
          <div className="flex-1 overflow-y-auto bg-gray-50 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-4xl space-y-4">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {error}
                </div>
              )}
              {messages.length === 0 && !sending && (
                <div className="text-center text-gray-500 py-8">
                  <p className="text-lg font-medium mb-2">Start the conversation</p>
                  <p className="text-sm">
                    Begin by introducing yourself and following the SPIKES framework
                  </p>
                </div>
              )}
              {messages.map((message) => (
                <ChatBubble key={message.id} message={message} onReplayAudio={playAssistantAudio} />
              ))}
              {showPatientRespondingIndicator && (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <div className="h-2 w-2 animate-pulse rounded-full bg-gray-400" />
                  Patient is responding...
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input */}
          <div className="border-t bg-white px-4 py-4 sm:px-6 lg:px-8">
            <form onSubmit={handleSubmit} className="mx-auto max-w-4xl">
              <div className="flex items-center gap-2">
                <Input
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Type your message following the SPIKES framework..."
                  disabled={sending || isRecording}
                  className="h-12 flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={handleVoiceInput}
                  disabled={sending || closing || !sessionId}
                  className={isRecording ? 'h-12 w-12 shrink-0 border-red-500 bg-red-50 text-red-600 shadow-[0_0_0_4px_rgba(239,68,68,0.12)]' : 'h-12 w-12 shrink-0'}
                  title={isRecording ? 'Stop recording' : 'Start voice input'}
                >
                  <Mic className="h-5 w-5" />
                </Button>
                <Button
                  type="submit"
                  size="icon"
                  disabled={sending || closing || isRecording || !inputValue.trim() || !sessionId}
                  className="h-12 w-12 shrink-0"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              <div className="mt-2 flex justify-between items-center text-xs text-gray-500">
                <span>Session time: {formatTime(sessionElapsed)} • SPIKES: {currentSpikesStage}</span>
                {sessionId && <span>Session ID: {sessionId}</span>}
              </div>
              <label className="mt-3 inline-flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={audioResponsesEnabled}
                  onChange={(e) => setAudioResponsesEnabled(e.target.checked)}
                  disabled={sending || closing}
                  className="h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                />
                <span>Audio responses</span>
                <span className="text-xs text-gray-500">Off by default</span>
              </label>
              {error && (
                <div className="mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {error}
                </div>
              )}
              <div
                className={`overflow-hidden transition-all duration-300 ease-out ${showVoiceIndicator ? 'mt-3 max-h-24 translate-y-0 opacity-100' : 'mt-0 max-h-0 -translate-y-1 opacity-0'}`}
              >
                <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900 transition-colors duration-200">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
                      <div>
                        <div className="font-medium">Listening</div>
                        <div className="text-xs text-emerald-700">
                          Tap the microphone again when you are done speaking.
                        </div>
                      </div>
                    </div>
                    <div className="flex h-8 w-16 items-end justify-end gap-1">
                      {listeningBarHeights.map((height, index) => (
                        <span
                          key={`voice-bar-${index}`}
                          className="w-1.5 origin-bottom rounded-full bg-emerald-500"
                          style={{
                            height,
                            animation: `listening-wave 0.9s ease-in-out ${index * 0.12}s infinite`,
                          }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </form>
          </div>
        </main>
      </div>
    </div>
  )
}

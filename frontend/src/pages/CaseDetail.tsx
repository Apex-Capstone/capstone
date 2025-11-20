import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getCase } from '@/api/cases.api'
import { createSession, submitTurn } from '@/api/sessions.api'
import type { Case as CaseType } from '@/types/case'
import type { Message } from '@/types/session'

import { ChatBubble } from '@/components/ChatBubble'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Mic, Send, Clock, PhoneOff } from 'lucide-react'

export const CaseDetail = () => {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()

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

  // --- Load case and create session ---
  useEffect(() => {
    const initializeSession = async () => {
      if (!caseId) return
      try {
        // Load case data
        const data = await getCase(Number(caseId))
        setCaseData(data)

        // Create a new session for this case
        const session = await createSession(Number(caseId))
        setSessionId(session.id)
        setCurrentSpikesStage(session.currentSpikesStage || 'setting')

        // Start timer
        const now = new Date()
        setStartTime(now)
        setSessionElapsed(0)
      } catch (error) {
        console.error('Failed to initialize session:', error)
        setError('Failed to start session. Please try again.')
      } finally {
        setLoading(false)
      }
    }
    initializeSession()
  }, [caseId])

  // --- Timer updates every second ---
  useEffect(() => {
    if (!startTime) return
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime.getTime()) / 1000)
      setSessionElapsed(elapsed)
    }, 1000)
    return () => clearInterval(timer)
  }, [startTime])

  // --- Message submission ---
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || sending || !sessionId) return

    const userMessageContent = inputValue
    setInputValue('')
    setSending(true)
    setError(null)

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
      const response = await submitTurn(sessionId, userMessageContent)
      
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
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (error: any) {
      console.error('Failed to submit turn:', error)
      setError(error.response?.data?.detail || 'Failed to send message. Please try again.')
      
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

  const handleVoiceInput = () => {
    alert('Voice input will be implemented when ASR backend is ready')
  }

  const handleEndSession = () => {
    if (sessionId) {
      navigate(`/feedback/${sessionId}`)
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

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
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 md:ml-64 flex flex-col">
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
                className="flex items-center gap-2"
              >
                <PhoneOff className="h-4 w-4" />
                End Session
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
                  <CardTitle className="text-sm font-medium">SPIKES Stage</CardTitle>
                </CardHeader>
                <CardContent className="pt-0 text-orange-700 font-semibold capitalize">
                  {currentSpikesStage}
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
                <ChatBubble key={message.id} message={message} />
              ))}
              {sending && (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <div className="h-2 w-2 animate-pulse rounded-full bg-gray-400" />
                  Patient is responding...
                </div>
              )}
            </div>
          </div>

          {/* Input */}
          <div className="border-t bg-white px-4 py-4 sm:px-6 lg:px-8">
            <form onSubmit={handleSubmit} className="mx-auto max-w-4xl">
              <div className="flex gap-2">
                <Input
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Type your message following the SPIKES framework..."
                  disabled={sending}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={handleVoiceInput}
                  disabled
                  className="opacity-50 cursor-not-allowed"
                  title="Voice input coming soon"
                >
                  <Mic className="h-4 w-4" />
                </Button>
                <Button type="submit" disabled={sending || !inputValue.trim() || !sessionId}>
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              <div className="mt-2 flex justify-between items-center text-xs text-gray-500">
                <span>Session time: {formatTime(sessionElapsed)} • SPIKES: {currentSpikesStage}</span>
                {sessionId && <span>Session ID: {sessionId}</span>}
              </div>
            </form>
          </div>
        </main>
      </div>
    </div>
  )
}

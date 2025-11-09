import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getCase } from '@/api/cases.api'
import type { Case as CaseType } from '@/types/case'
import type { Message } from '@/api/client' // use your Message type

import { ChatBubble } from '@/components/ChatBubble'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Mic, Send, Clock, User, Brain, PhoneOff } from 'lucide-react'
import { cn } from '@/lib/utils'

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

  // --- Load case from backend ---
  useEffect(() => {
    const loadCase = async () => {
      if (!caseId) return
      try {
        const data = await getCase(Number(caseId))
        setCaseData(data)

        // 🕒 Mock session start if backend doesn't send one
        const now = new Date()
        setStartTime(now)

        // Initialize timer to 0 (fresh session)
        setSessionElapsed(0)
      } catch (error) {
        console.error('Failed to fetch case:', error)
      } finally {
        setLoading(false)
      }
    }
    loadCase()
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
    if (!inputValue.trim() || sending) return

    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, newMessage])
    setInputValue('')
    setSending(true)

    // Mock AI reply
    setTimeout(() => {
      const response: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content:
          'This is a placeholder response. When the backend chat endpoint is ready, this will show the actual AI reply.',
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, response])
      setSending(false)
    }, 800)
  }

  const handleVoiceInput = () => {
    alert('Voice input will be implemented when ASR backend is ready')
  }

  const handleEndSession = () => {
    const sessionId = `session_${caseId}_${Date.now()}`
    navigate(`/feedback/${sessionId}`)
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
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
            </div>

            {/* Script */}
            <div className="mt-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Script</CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <pre className="whitespace-pre-wrap text-sm text-gray-800">
                    {caseData.script}
                  </pre>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Chat area */}
          <div className="flex-1 overflow-y-auto bg-gray-50 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-4xl space-y-4">
              {messages.map((message) => (
                <ChatBubble key={message.id} message={message} />
              ))}
              {sending && (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <div className="h-2 w-2 animate-pulse rounded-full bg-gray-400" />
                  Assistant is typing...
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
                <Button type="submit" disabled={sending || !inputValue.trim()}>
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              <div className="mt-2 flex justify-between items-center text-xs text-gray-500">
                <span>Session time: {formatTime(sessionElapsed)}</span>
                <span>Last updated: {new Date(caseData.updatedAt).toLocaleString()}</span>
              </div>
            </form>
          </div>
        </main>
      </div>
    </div>
  )
}

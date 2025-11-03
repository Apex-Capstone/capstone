import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchCase } from '@/api/client'
import type { CaseDetail as CaseDetailType, Message } from '@/api/client'
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
  const [caseData, setCaseData] = useState<CaseDetailType | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [sessionElapsed, setSessionElapsed] = useState(0)

  useEffect(() => {
    const loadCase = async () => {
      if (!caseId) return

      try {
        const data = await fetchCase(caseId)
        setCaseData(data)
        setMessages(data.messages)
        
        // TODO: FR-3, FR-4, FR-5 - Initialize session timer
        if (data.sessionTimer) {
          const elapsed = Math.floor((Date.now() - new Date(data.sessionTimer.startTime).getTime()) / 1000)
          setSessionElapsed(elapsed)
        }
      } catch (error) {
        console.error('Failed to fetch case:', error)
      } finally {
        setLoading(false)
      }
    }

    loadCase()
  }, [caseId])

  // TODO: FR-3, FR-4, FR-5 - Session timer update
  useEffect(() => {
    if (!caseData?.sessionTimer) return
    
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - new Date(caseData.sessionTimer!.startTime).getTime()) / 1000)
      setSessionElapsed(elapsed)
    }, 1000)

    return () => clearInterval(timer)
  }, [caseData?.sessionTimer])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || sending) return

    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString(),
    }

    setMessages([...messages, newMessage])
    setInputValue('')
    setSending(true)

    // TODO: Replace with actual API call to send message
    // await sendMessage(caseId, inputValue)
    
    // Simulate response
    setTimeout(() => {
      const response: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'This is a placeholder response. When the FastAPI backend is connected, this will send your message and receive the actual AI response.',
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, response])
      setSending(false)
    }, 1000)
  }

  const handleVoiceInput = () => {
    // TODO: Implement voice input functionality
    alert('Voice input will be implemented when backend is ready')
  }

  const handleEndSession = () => {
    // TODO: FR-10 - End session and redirect to feedback
    const sessionId = `session_${caseId}_${Date.now()}`
    navigate(`/feedback/${sessionId}`)
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const emotionConfig = {
    anxious: { label: 'Anxious', color: 'text-orange-700 bg-orange-100' },
    withdrawn: { label: 'Withdrawn', color: 'text-purple-700 bg-purple-100' },
    angry: { label: 'Angry', color: 'text-red-700 bg-red-100' },
    confused: { label: 'Confused', color: 'text-yellow-700 bg-yellow-100' },
    cooperative: { label: 'Cooperative', color: 'text-green-700 bg-green-100' },
  }

  const spikesStages = {
    setting: 'Setting & Privacy',
    perception: 'Patient Perception',
    invitation: 'Invitation to Share',
    knowledge: 'Knowledge Sharing',
    emotions: 'Emotions & Empathy',
    strategy: 'Strategy & Summary'
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
          {/* TODO: FR-3, FR-4, FR-5 - Enhanced case header with patient info and session data */}
          <div className="border-b bg-white px-4 py-4 sm:px-6 lg:px-8">
            <nav className="mb-3 text-sm text-gray-500">
              <span>Dashboard</span> / <span className="text-gray-900">Case Detail</span>
            </nav>
            
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{caseData.title}</h1>
                <p className="mt-1 text-sm text-gray-600">{caseData.description}</p>
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

            {/* Patient and session info */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Patient Demographics */}
              {caseData.patientDemographics && (
                <Card className="bg-emerald-50 border-emerald-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <User className="h-4 w-4" />
                      Patient Information
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="space-y-1 text-sm">
                      <div>
                        <span className="font-medium">Age:</span> {caseData.patientDemographics.age} years
                      </div>
                      <div>
                        <span className="font-medium">Gender:</span> {caseData.patientDemographics.gender}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">Emotion:</span>
                        {caseData.patientDemographics.emotion && emotionConfig[caseData.patientDemographics.emotion] && (
                          <span className={cn(
                            'px-2 py-0.5 rounded-full text-xs font-medium',
                            emotionConfig[caseData.patientDemographics.emotion].color
                          )}>
                            {emotionConfig[caseData.patientDemographics.emotion].label}
                          </span>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Session Timer */}
              <Card className="bg-green-50 border-green-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Session Timer
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="text-2xl font-bold text-green-700">
                    {formatTime(sessionElapsed)}
                  </div>
                  <div className="text-xs text-green-600 mt-1">
                    Active session
                  </div>
                </CardContent>
              </Card>

              {/* SPIKES Stage */}
              <Card className="bg-purple-50 border-purple-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Brain className="h-4 w-4" />
                    SPIKES Framework
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="text-sm font-medium text-purple-700">
                    {caseData.currentSpikesStage && spikesStages[caseData.currentSpikesStage as keyof typeof spikesStages]}
                  </div>
                  <div className="text-xs text-purple-600 mt-1">
                    Current stage
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

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
                {/* TODO: FR-3 - Microphone button placeholder (disabled until ASR integration) */}
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={handleVoiceInput}
                  disabled={true}
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
                <span>Voice input will be available when ASR backend is integrated</span>
                <div className="flex items-center gap-4">
                  <span>Session: {formatTime(sessionElapsed)}</span>
                  <span>•</span>
                  <span>SPIKES: {caseData.currentSpikesStage && spikesStages[caseData.currentSpikesStage as keyof typeof spikesStages]}</span>
                </div>
              </div>
            </form>
          </div>
        </main>
      </div>
    </div>
  )
}


import { useCallback, useEffect, useRef, useState } from 'react'
import { buildSessionWebSocketUrl, toRealtimeTurnPayload } from '@/api/sessions.api'
import type {
  ConversationConnectionStatus,
  RealtimeServerMessage,
} from '@/types/session'

interface UseRealtimeSessionOptions {
  enabled: boolean
  sessionId: number | null
  token: string | null
  onAssistantMessage?: (payload: {
    content: string
    turnId?: number
    spikesStage?: string
    assistantAudioUrl?: string
  }) => void
  onStageUpdate?: (stage: string) => void
  onError?: (message: string) => void
}

interface UseRealtimeSessionResult {
  connectionStatus: ConversationConnectionStatus
  isConnected: boolean
  isPatientResponding: boolean
  sendTextTurn: (text: string, enableTts?: boolean) => boolean
}

/**
 * Opens a session websocket only while conversation mode is enabled.
 */
export const useRealtimeSession = ({
  enabled,
  sessionId,
  token,
  onAssistantMessage,
  onStageUpdate,
  onError,
}: UseRealtimeSessionOptions): UseRealtimeSessionResult => {
  const socketRef = useRef<WebSocket | null>(null)
  const [connectionStatus, setConnectionStatus] =
    useState<ConversationConnectionStatus>('disabled')
  const [isPatientResponding, setIsPatientResponding] = useState(false)

  useEffect(() => {
    if (!enabled) {
      socketRef.current?.close()
      socketRef.current = null
      setIsPatientResponding(false)
      setConnectionStatus('disabled')
      return
    }

    if (!sessionId || !token) {
      setConnectionStatus('disconnected')
      return
    }

    const socket = new WebSocket(buildSessionWebSocketUrl(sessionId, token))
    socketRef.current = socket
    setConnectionStatus('connecting')

    socket.onopen = () => {
      if (socketRef.current !== socket) return
      setConnectionStatus('connected')
    }

    socket.onmessage = (event) => {
      let payload: RealtimeServerMessage

      try {
        payload = JSON.parse(event.data) as RealtimeServerMessage
      } catch {
        setConnectionStatus('error')
        setIsPatientResponding(false)
        onError?.('Conversation mode returned an invalid server message.')
        return
      }

      if (payload.type === 'assistant_message') {
        setIsPatientResponding(false)
        onAssistantMessage?.({
          content: payload.content,
          turnId: payload.meta?.turn_id,
          spikesStage: payload.meta?.spikes_stage,
          assistantAudioUrl: payload.meta?.assistant_audio_url ?? undefined,
        })
        return
      }

      if (payload.type === 'stage_update' && payload.meta?.spikes_stage) {
        onStageUpdate?.(payload.meta.spikes_stage)
        return
      }

      if (payload.type === 'error') {
        setIsPatientResponding(false)
        onError?.(payload.content || 'Conversation mode failed to process the message.')
      }
    }

    socket.onerror = () => {
      if (socketRef.current !== socket) return
      setConnectionStatus('error')
    }

    socket.onclose = () => {
      if (socketRef.current === socket) {
        socketRef.current = null
      }
      setIsPatientResponding(false)
      setConnectionStatus(enabled ? 'disconnected' : 'disabled')
    }

    return () => {
      if (socketRef.current === socket) {
        socketRef.current = null
      }
      socket.close()
    }
  }, [enabled, onAssistantMessage, onError, onStageUpdate, sessionId, token])

  const sendTextTurn = useCallback(
    (text: string, enableTts = false) => {
      const socket = socketRef.current
      if (!enabled || socket === null || socket.readyState !== WebSocket.OPEN) {
        return false
      }

      try {
        socket.send(JSON.stringify(toRealtimeTurnPayload(text, enableTts)))
        setIsPatientResponding(true)
        return true
      } catch {
        setConnectionStatus('error')
        setIsPatientResponding(false)
        return false
      }
    },
    [enabled]
  )

  return {
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    isPatientResponding,
    sendTextTurn,
  }
}

/**
 * Single chat message row with optional assistant audio replay.
 */
import type { Message } from '@/types/session'
import { cn } from '@/lib/utils'
import { User, Bot, Volume2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

/** Props for {@link ChatBubble}. */
interface ChatBubbleProps {
  message: Message
  /** Invoked when the user taps replay on assistant audio. */
  onReplayAudio?: (audioUrl: string) => void
}

/**
 * Renders a user or assistant bubble with timestamp and source label.
 *
 * @param props - {@link ChatBubbleProps}
 * @returns Message row JSX
 */
export const ChatBubble = ({ message, onReplayAudio }: ChatBubbleProps) => {
  const isUser = message.role === 'user'
  const assistantAudioUrl = message.assistantAudioUrl

  return (
    <div
      className={cn(
        'flex w-full items-start gap-3',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100">
          <Bot className="h-4 w-4 text-emerald-600" />
        </div>
      )}

      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-2',
          isUser
            ? 'bg-emerald-600 text-white'
            : 'bg-gray-100 text-gray-900'
        )}
      >
        <p
          className={cn(
            'text-sm whitespace-pre-wrap',
            message.status === 'pending' && 'italic opacity-90',
            message.status === 'error' && 'font-medium'
          )}
        >
          {message.content}
        </p>
        <p
          className={cn(
            'mt-1 text-xs',
            isUser ? 'text-emerald-100' : 'text-gray-500'
          )}
        >
          {message.source === 'audio' ? 'Voice' : 'Text'} • {new Date(message.timestamp).toLocaleTimeString()}
        </p>
        {!isUser && assistantAudioUrl && onReplayAudio && (
          <Button
            type="button"
            onClick={() => onReplayAudio(assistantAudioUrl)}
            variant="neutral"
            size="sm"
            className="mt-2 h-8 gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-3 text-xs font-medium text-emerald-700 hover:bg-emerald-100 hover:text-emerald-800"
          >
            <Volume2 className="h-3.5 w-3.5" />
            Replay audio
          </Button>
        )}
      </div>

      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-200">
          <User className="h-4 w-4 text-gray-600" />
        </div>
      )}
    </div>
  )
}


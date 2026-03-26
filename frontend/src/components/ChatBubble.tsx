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
  const voiceToneLabels =
    message.voiceTone?.labels?.filter((label) => label.toLowerCase() !== 'unclear').slice(0, 2) ?? []

  return (
    <div
      className={cn(
        'flex w-full items-end gap-3',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      {!isUser && (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-apex-100 bg-apex-50 shadow-sm">
          <Bot className="h-4 w-4 text-apex-600" />
        </div>
      )}

      <div
        className={cn(
          'max-w-[88%] rounded-[22px] px-4 py-3 shadow-sm sm:max-w-[82%] xl:max-w-[78%]',
          isUser
            ? 'bg-apex-600 text-white'
            : 'border border-slate-200 bg-white text-gray-900'
        )}
      >
        <p
          className={cn(
            'whitespace-pre-wrap text-sm leading-6',
            message.status === 'pending' && 'italic opacity-90',
            message.status === 'error' && 'font-medium'
          )}
        >
          {message.content}
        </p>
        <p
          className={cn(
            'mt-1 text-xs',
            isUser ? 'text-apex-100' : 'text-gray-500'
          )}
        >
          {message.source === 'audio' ? 'Voice' : 'Text'} • {new Date(message.timestamp).toLocaleTimeString()}
        </p>
        {isUser && message.source === 'audio' && voiceToneLabels.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {voiceToneLabels.map((label) => (
              <span
                key={label}
                className="rounded-full bg-apex-500/80 px-2 py-0.5 text-[10px] font-medium text-apex-50"
              >
                {label}
              </span>
            ))}
          </div>
        )}
        {!isUser && assistantAudioUrl && onReplayAudio && (
          <Button
            type="button"
            onClick={() => onReplayAudio(assistantAudioUrl)}
            variant="neutral"
            size="sm"
            className="mt-2 h-8 gap-1 rounded-full border border-apex-200 bg-apex-50 px-3 text-xs font-medium text-apex-700 hover:bg-apex-100 hover:text-apex-800"
          >
            <Volume2 className="h-3.5 w-3.5" />
            Replay audio
          </Button>
        )}
      </div>

      {isUser && (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-slate-100 shadow-sm">
          <User className="h-4 w-4 text-gray-600" />
        </div>
      )}
    </div>
  )
}


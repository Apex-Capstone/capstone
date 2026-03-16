import type { Message } from '@/types/session'
import { cn } from '@/lib/utils'
import { User, Bot } from 'lucide-react'

interface ChatBubbleProps {
  message: Message
}

export const ChatBubble = ({ message }: ChatBubbleProps) => {
  const isUser = message.role === 'user'

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
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        <p
          className={cn(
            'mt-1 text-xs',
            isUser ? 'text-emerald-100' : 'text-gray-500'
          )}
        >
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>
      </div>

      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-200">
          <User className="h-4 w-4 text-gray-600" />
        </div>
      )}
    </div>
  )
}


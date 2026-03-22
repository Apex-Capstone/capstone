/**
 * Horizontal SPIKES stage indicator for session UI.
 */
import { CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'

type SpikesStageId = 'setting' | 'perception' | 'invitation' | 'knowledge' | 'emotion' | 'strategy'

/** Ordered SPIKES stages for the progress visualization. */
const STAGES: { id: SpikesStageId; label: string }[] = [
  { id: 'setting', label: 'Setting' },
  { id: 'perception', label: 'Perception' },
  { id: 'invitation', label: 'Invitation' },
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'emotion', label: 'Emotion' },
  { id: 'strategy', label: 'Strategy' },
]

/** Props for {@link SpikesProgressBar}. */
interface SpikesProgressBarProps {
  /** Raw stage string from the backend (matched case-insensitively). */
  currentStage?: string
}

/**
 * Shows six SPIKES checkpoints with completion/current/empty styling.
 *
 * @param props - {@link SpikesProgressBarProps}
 * @returns Progress bar JSX
 */
export const SpikesProgressBar = ({ currentStage }: SpikesProgressBarProps) => {
  const normalizedStage = currentStage?.toLowerCase() as SpikesStageId | undefined
  const currentIndex = STAGES.findIndex((s) => s.id === normalizedStage)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs font-medium text-gray-700">
        <span>SPIKES Progress</span>
        <span className="capitalize text-gray-600">
          {currentIndex >= 0 ? STAGES[currentIndex].label : 'Not started'}
        </span>
      </div>
      <div className="flex items-center justify-between gap-2">
        {STAGES.map((stage, index) => {
          const isCompleted = currentIndex >= 0 && index < currentIndex
          const isCurrent = currentIndex === index

          return (
            <div key={stage.id} className="flex flex-1 flex-col items-center gap-1">
              <div
                className={cn(
                  'flex h-7 w-7 items-center justify-center rounded-full border text-[10px] font-semibold',
                  isCompleted && 'border-emerald-500 bg-emerald-500 text-white',
                  isCurrent &&
                    !isCompleted &&
                    'border-emerald-500 bg-emerald-50 text-emerald-700 ring-2 ring-emerald-100',
                  !isCompleted && !isCurrent && 'border-gray-200 bg-gray-50 text-gray-400'
                )}
              >
                {isCompleted ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  stage.label[0]
                )}
              </div>
              <span
                className={cn(
                  'truncate text-[10px]',
                  isCompleted && 'text-emerald-700',
                  isCurrent && !isCompleted && 'text-emerald-700',
                  !isCompleted && !isCurrent && 'text-gray-400'
                )}
              >
                {stage.label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}


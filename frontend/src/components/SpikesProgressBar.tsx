/**
 * Horizontal SPIKES stage indicator for session UI.
 */
import { cn } from '@/lib/utils'

type SpikesStageId = 'setting' | 'perception' | 'invitation' | 'knowledge' | 'emotion' | 'strategy'

/** Ordered SPIKES stages for the session overview indicator. */
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
 * Shows six SPIKES checkpoints and underlines only the active stage.
 *
 * @param props - {@link SpikesProgressBarProps}
 * @returns Progress bar JSX
 */
export const SpikesProgressBar = ({ currentStage }: SpikesProgressBarProps) => {
  const normalizedStage = currentStage?.toLowerCase() as SpikesStageId | undefined
  const currentIndex = STAGES.findIndex((s) => s.id === normalizedStage)

  return (
    <div className="space-y-0.5">
      <div className="grid grid-cols-6 gap-2 sm:gap-2.5">
        {STAGES.map((stage, index) => {
          const isCurrent = currentIndex === index
          const isCompleted = currentIndex >= 0 && index < currentIndex

          return (
            <div key={stage.id} className="flex min-w-0 flex-col items-center gap-2 text-center">
              <div
                className={cn(
                  'flex h-9 w-9 items-center justify-center rounded-full border text-xs font-medium',
                  isCompleted && 'border-apex-200 bg-apex-50 text-apex-700',
                  isCurrent && 'border-apex-500 bg-apex-50 text-apex-700 ring-2 ring-apex-100',
                  !isCompleted && !isCurrent && 'border-slate-200 bg-slate-50 text-slate-400'
                )}
              >
                {stage.label[0]}
              </div>
              <span
                className={cn(
                  'min-h-[22px] w-full px-0.5 text-center text-[8.5px] leading-tight whitespace-normal sm:text-[9.5px]',
                  isCompleted && 'text-apex-700',
                  isCurrent && 'font-semibold text-apex-700',
                  !isCompleted && !isCurrent && 'text-slate-500'
                )}
              >
                {stage.label}
              </span>
              <div
                className={cn(
                  'h-1 w-full rounded-full transition-colors duration-300 ease-out',
                  isCurrent || isCompleted ? 'bg-apex-500' : 'bg-slate-200'
                )}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}


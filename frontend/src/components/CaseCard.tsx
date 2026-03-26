import type { KeyboardEvent } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card'
import type { Case } from '@/types/case'
import { formatDateInUserTimeZone } from '@/lib/dateTime'
import { cn } from '@/lib/utils'

const difficultyConfig: Record<string, { label: string; color: string }> = {
  beginner: { label: 'Beginner', color: 'text-apex-700 bg-apex-100' },
  intermediate: { label: 'Intermediate', color: 'text-amber-700 bg-amber-100' },
  advanced: { label: 'Advanced', color: 'text-rose-700 bg-rose-100' },
}

interface CaseCardProps {
  caseData: Case
  onClick?: (caseId: number) => void
  /** Highlights the card (e.g. while starting a session). */
  selected?: boolean
}

export const CaseCard = ({ caseData, onClick, selected }: CaseCardProps) => {
  const difficultyKey = caseData.difficultyLevel?.toLowerCase()
  const difficulty = difficultyKey ? difficultyConfig[difficultyKey] : null

  const activate = () => onClick?.(caseData.id)

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      activate()
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      className={cn(
        'cursor-pointer rounded-lg outline-none transition-shadow',
        'focus-visible:ring-2 focus-visible:ring-apex-500 focus-visible:ring-offset-2'
      )}
      onClick={activate}
      onKeyDown={onKeyDown}
    >
      <Card
        className={cn(
          'h-full transition-shadow hover:shadow-md',
          selected
            ? 'border-2 border-apex-500 hover:border-apex-500'
            : 'border border-gray-200 hover:border-apex-300'
        )}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between mb-2">
            <CardTitle className="text-lg leading-tight">{caseData.title}</CardTitle>
            {caseData.difficultyLevel && (
              <span
                className={cn(
                  'px-2 py-0.5 rounded-full text-xs font-medium',
                  difficulty ? difficulty.color : 'bg-gray-100 text-gray-700'
                )}
              >
                {difficulty ? difficulty.label : caseData.difficultyLevel}
              </span>
            )}
          </div>

          {caseData.description && (
            <CardDescription className="line-clamp-2 text-sm">
              {caseData.description}
            </CardDescription>
          )}
        </CardHeader>

        <CardContent className="pt-0">
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span>Created: {formatDateInUserTimeZone(caseData.createdAt)}</span>
            {caseData.updatedAt !== caseData.createdAt && (
              <span>Updated: {formatDateInUserTimeZone(caseData.updatedAt)}</span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

import type { KeyboardEvent } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card'
import type { Case } from '@/types/case'
import { cn } from '@/lib/utils'

const difficultyConfig: Record<string, { label: string; color: string }> = {
  beginner: { label: 'Beginner', color: 'text-emerald-700 bg-emerald-100' },
  intermediate: { label: 'Intermediate', color: 'text-yellow-700 bg-yellow-100' },
  advanced: { label: 'Advanced', color: 'text-red-700 bg-red-100' },
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
        'focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2'
      )}
      onClick={activate}
      onKeyDown={onKeyDown}
    >
      <Card
        className={cn(
          'h-full transition hover:shadow-md',
          selected
            ? 'border-2 border-green-500 hover:border-green-500'
            : 'border border-gray-200 hover:border-green-400'
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
            <span>Created: {new Date(caseData.createdAt).toLocaleDateString()}</span>
            {caseData.updatedAt !== caseData.createdAt && (
              <span>Updated: {new Date(caseData.updatedAt).toLocaleDateString()}</span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

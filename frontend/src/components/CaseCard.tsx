import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card'
import type { Case } from '@/types/case'
import { cn } from '@/lib/utils'

const difficultyConfig: Record<string, { label: string; color: string }> = {
  beginner: { label: 'Beginner', color: 'text-emerald-700 bg-emerald-100' },
  intermediate: { label: 'Intermediate', color: 'text-amber-700 bg-amber-100' },
  advanced: { label: 'Advanced', color: 'text-rose-700 bg-rose-100' },
}

interface CaseCardProps {
  caseData: Case
  onClick?: (caseId: number) => void
}

export const CaseCard = ({ caseData, onClick }: CaseCardProps) => {
  const difficultyKey = caseData.difficultyLevel?.toLowerCase()
  const difficulty = difficultyKey ? difficultyConfig[difficultyKey] : null

  return (
    <div
      className="cursor-pointer"
      onClick={() => onClick?.(caseData.id)}
    >
      <Card className="h-full transition-shadow hover:shadow-md hover:border-emerald-300">
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
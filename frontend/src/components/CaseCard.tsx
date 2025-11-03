import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card'
import type { Case } from '@/api/client'
import { cn } from '@/lib/utils'
import { Clock, CheckCircle2, AlertCircle } from 'lucide-react'

interface CaseCardProps {
  caseData: Case
}

const statusConfig = {
  in_progress: {
    label: 'In Progress',
    icon: Clock,
    color: 'text-emerald-600 bg-emerald-50',
  },
  completed: {
    label: 'Completed',
    icon: CheckCircle2,
    color: 'text-green-600 bg-green-50',
  },
  pending: {
    label: 'Available',
    icon: AlertCircle,
    color: 'text-gray-600 bg-gray-50',
  },
}

const emotionConfig = {
  anxious: { label: 'Anxious', color: 'text-orange-700 bg-orange-100' },
  withdrawn: { label: 'Withdrawn', color: 'text-purple-700 bg-purple-100' },
  angry: { label: 'Angry', color: 'text-red-700 bg-red-100' },
  confused: { label: 'Confused', color: 'text-yellow-700 bg-yellow-100' },
  cooperative: { label: 'Cooperative', color: 'text-green-700 bg-green-100' },
}

const difficultyConfig = {
  beginner: { label: 'Beginner', color: 'text-emerald-700 bg-emerald-100' },
  intermediate: { label: 'Intermediate', color: 'text-amber-700 bg-amber-100' },
  advanced: { label: 'Advanced', color: 'text-rose-700 bg-rose-100' },
}

export const CaseCard = ({ caseData }: CaseCardProps) => {
  const status = statusConfig[caseData.status]
  const StatusIcon = status.icon
  const difficulty = caseData.difficulty ? difficultyConfig[caseData.difficulty] : null
  const emotion = caseData.patientDemographics?.emotion ? emotionConfig[caseData.patientDemographics.emotion] : null

  return (
    <Link to={`/case/${caseData.id}`}>
      <Card className="h-full transition-shadow hover:shadow-md hover:border-emerald-300">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between mb-2">
            <CardTitle className="text-lg leading-tight">{caseData.title}</CardTitle>
            <span
              className={cn(
                'flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
                status.color
              )}
            >
              <StatusIcon className="h-3 w-3" />
              {status.label}
            </span>
          </div>
          
          {/* TODO: FR-2 - Enhanced case display with demographics and SPIKES data */}
          {caseData.patientDemographics && (
            <div className="flex items-center gap-2 mb-2 text-sm text-gray-600">
              <span>{caseData.patientDemographics.age}y</span>
              <span>•</span>
              <span className="capitalize">{caseData.patientDemographics.gender}</span>
              {emotion && (
                <>
                  <span>•</span>
                  <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', emotion.color)}>
                    {emotion.label}
                  </span>
                </>
              )}
            </div>
          )}
          
          {caseData.description && (
            <CardDescription className="line-clamp-2 text-sm">
              {caseData.description}
            </CardDescription>
          )}
        </CardHeader>
        
        <CardContent className="pt-0">
          <div className="space-y-3">
            {/* SPIKES stage and difficulty */}
            <div className="flex items-center justify-between">
              {caseData.spikesStage && (
                <div className="text-xs text-gray-500">
                  <span className="font-medium">SPIKES:</span> {caseData.spikesStage.charAt(0).toUpperCase() + caseData.spikesStage.slice(1)}
                </div>
              )}
              {difficulty && (
                <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', difficulty.color)}>
                  {difficulty.label}
                </span>
              )}
            </div>
            
            {/* Timestamps */}
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span>Created: {new Date(caseData.createdAt).toLocaleDateString()}</span>
              {caseData.updatedAt !== caseData.createdAt && (
                <span>Updated: {new Date(caseData.updatedAt).toLocaleDateString()}</span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}


import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card'
//import type { Case } from '@/api/client'
import type { Case } from '@/types/case'
// import { cn } from '@/lib/utils'
// import { Clock, CheckCircle2, AlertCircle } from 'lucide-react'

// interface CaseCardProps {
//   caseData: Case
// }

// const statusConfig = {
//   in_progress: {
//     label: 'In Progress',
//     icon: Clock,
//     color: 'text-emerald-600 bg-emerald-50',
//   },
//   completed: {
//     label: 'Completed',
//     icon: CheckCircle2,
//     color: 'text-green-600 bg-green-50',
//   },
//   pending: {
//     label: 'Available',
//     icon: AlertCircle,
//     color: 'text-gray-600 bg-gray-50',
//   },
// }

// const emotionConfig = {
//   anxious: { label: 'Anxious', color: 'text-orange-700 bg-orange-100' },
//   withdrawn: { label: 'Withdrawn', color: 'text-purple-700 bg-purple-100' },
//   angry: { label: 'Angry', color: 'text-red-700 bg-red-100' },
//   confused: { label: 'Confused', color: 'text-yellow-700 bg-yellow-100' },
//   cooperative: { label: 'Cooperative', color: 'text-green-700 bg-green-100' },
// }

// const difficultyConfig = {
//   beginner: { label: 'Beginner', color: 'text-emerald-700 bg-emerald-100' },
//   intermediate: { label: 'Intermediate', color: 'text-amber-700 bg-amber-100' },
//   advanced: { label: 'Advanced', color: 'text-rose-700 bg-rose-100' },
// }
export const CaseCard = ({ caseData }: { caseData: Case }) => {
  return (
    <Link to={`/case/${caseData.id}`}>
      <Card className="h-full transition-shadow hover:shadow-md hover:border-emerald-300">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between mb-2">
            <CardTitle className="text-lg leading-tight">{caseData.title}</CardTitle>
            {caseData.difficultyLevel && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                {caseData.difficultyLevel}
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
    </Link>
  )
}
import type { ComponentType } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

type StatsCardProps = {
  icon: ComponentType<{ className?: string }>
  title: string
  value: string | number
  valueClassName?: string
}

export function StatsCard({ icon: Icon, title, value, valueClassName }: StatsCardProps) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-2">
          <Icon className="h-5 w-5 text-gray-700" />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-medium text-gray-600">{title}</div>
          <div className={cn(valueClassName ?? 'text-2xl font-bold text-gray-900')}>{value}</div>
        </div>
      </CardContent>
    </Card>
  )
}


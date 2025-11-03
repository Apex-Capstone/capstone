import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import type { ComponentType } from 'react'
// import { LucideIcon } from 'lucide-react'


interface MetricCardProps {
  title: string
  value: string | number
  icon?: ComponentType<{ className?: string }>
  description?: string
  trend?: {
    value: number
    isPositive: boolean
  }
}

export const MetricCard = ({
  title,
  value,
  icon: Icon,
  description,
  trend,
}: MetricCardProps) => {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {Icon && <Icon className="h-4 w-4 text-gray-500" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-gray-500 mt-1">{description}</p>
        )}
        {trend && (
          <p
            className={`text-xs mt-1 ${
              trend.isPositive ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {trend.isPositive ? '+' : ''}
            {trend.value}% from last period
          </p>
        )}
      </CardContent>
    </Card>
  )
}


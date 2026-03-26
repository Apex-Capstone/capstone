/**
 * Compact KPI tile with optional icon and trend line.
 */
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import type { ComponentType } from 'react'

/** Props for {@link MetricCard}. */
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

/**
 * Displays a titled metric value with optional description and trend percentage.
 *
 * @param props - {@link MetricCardProps}
 * @returns Card with metric content
 */
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
              trend.isPositive ? 'text-apex-600' : 'text-red-600'
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


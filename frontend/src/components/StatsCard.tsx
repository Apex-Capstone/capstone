import type { ComponentType } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { ArrowRight } from 'lucide-react'

type StatsCardProps = {
  icon: ComponentType<{ className?: string }>
  title: string
  value: string | number
  valueClassName?: string
  href?: string
  hintText?: string
}

export function StatsCard({ icon: Icon, title, value, valueClassName, href, hintText }: StatsCardProps) {
  const card = (
    <Card
      className={cn(
        'transition',
        href && 'cursor-pointer group hover:border-apex-300 hover:shadow-md'
      )}
    >
      <CardContent className="flex items-center gap-3 p-4">
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-2">
          <Icon className="h-5 w-5 text-gray-700" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium text-gray-600">{title}</div>
          <div className={cn(valueClassName ?? 'text-2xl font-bold text-gray-900')}>{value}</div>
        </div>
      </CardContent>
      {href && hintText && (
        <div className="px-4 pb-3 -mt-2">
          <span className="flex items-center gap-1 text-xs text-gray-400 opacity-0 translate-y-1 transition-all duration-200 group-hover:opacity-100 group-hover:translate-y-0">
            {hintText}
            <ArrowRight className="h-3 w-3" />
          </span>
        </div>
      )}
    </Card>
  )

  if (href) {
    return (
      <Link to={href} className="block no-underline text-inherit">
        {card}
      </Link>
    )
  }

  return card
}

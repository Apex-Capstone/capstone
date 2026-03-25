import { Link } from 'react-router-dom'

import { cn } from '@/lib/utils'

export type BreadcrumbItem = {
  label: string
  href?: string
}

type BreadcrumbProps = {
  items: BreadcrumbItem[]
  className?: string
}

/**
 * Inline breadcrumb trail with optional links and "/" separators.
 */
export function Breadcrumb({ items, className }: BreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" className={cn('mb-4 text-sm', className)}>
      {items.map((item, index) => (
        <span key={`${item.label}-${index}`}>
          {index > 0 && <span className="text-gray-500"> / </span>}
          {item.href ? (
            <Link
              to={item.href}
              className="cursor-pointer text-gray-500 underline-offset-2 hover:underline"
            >
              {item.label}
            </Link>
          ) : (
            <span className="text-gray-900">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}

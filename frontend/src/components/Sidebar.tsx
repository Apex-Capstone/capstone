/**
 * Role-filtered left navigation for primary app sections (desktop + mobile slide-over).
 */
import { Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { LayoutDashboard, FileText, Shield, BarChart3, Menu } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

/**
 * Renders sidebar links filtered by the current user's role.
 *
 * @remarks
 * `collapsed` hides the panel on small screens; a floating control can reopen it.
 * The `navigation` list is filtered to items whose `roles` includes the active role (default trainee).
 *
 * @returns Sidebar JSX or null when logged out
 */
export const Sidebar = () => {
  const { user, isAuthenticated } = useAuthStore()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  if (!isAuthenticated) return null

  const navigation = [
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: LayoutDashboard,
      roles: ['trainee', 'admin'],
    },
    {
      name: 'Cases',
      href: '/dashboard',
      icon: FileText,
      roles: ['trainee', 'admin'],
    },
    {
      name: 'Research',
      href: '/research',
      icon: BarChart3,
      roles: ['admin'],
    },
    {
      name: 'Admin',
      href: '/admin',
      icon: Shield,
      roles: ['admin'],
    },
  ].filter((item) => item.roles.includes(user?.role || 'trainee'))

  return (
    <div
      className={cn(
        'fixed left-0 top-16 z-40 h-[calc(100vh-4rem)] border-r bg-white transition-transform md:translate-x-0',
        collapsed ? '-translate-x-full' : 'translate-x-0'
      )}
    >
      <div className="flex h-full flex-col">
        <div className="flex h-16 items-center justify-between border-b px-4 md:hidden">
          <span className="text-sm font-semibold">Navigation</span>
          <button
            onClick={() => setCollapsed(true)}
            className="p-2 hover:bg-gray-100"
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-2 py-4">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  'flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-emerald-50 text-emerald-700'
                    : 'text-gray-700 hover:bg-gray-50'
                )}
              >
                <item.icon className="h-5 w-5" />
                <span>{item.name}</span>
              </Link>
            )
          })}
        </nav>
      </div>

      {collapsed && (
        <button
          onClick={() => setCollapsed(false)}
          className="fixed left-0 top-20 z-50 rounded-r-md border-r border-t border-b bg-white p-2 md:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>
      )}
    </div>
  )
}

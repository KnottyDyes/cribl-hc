import { Link, useLocation } from 'react-router-dom'
import {
  KeyIcon,
  BeakerIcon,
  DocumentChartBarIcon,
  SunIcon,
  MoonIcon,
} from '@heroicons/react/24/outline'
import { useTheme } from '../../hooks/useTheme'

export function Navbar() {
  const location = useLocation()
  const { resolvedTheme, toggleTheme } = useTheme()

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path)
  }

  const navItems = [
    { path: '/credentials', label: 'Credentials', icon: KeyIcon },
    { path: '/analysis', label: 'Analysis', icon: BeakerIcon },
    { path: '/results', label: 'Results', icon: DocumentChartBarIcon },
  ]

  const isDark = resolvedTheme === 'dark'

  return (
    <nav className={`shadow-sm border-b transition-colors duration-200 ${
      isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
    }`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="flex items-center">
              <span className="text-xl font-bold text-blue-500">Cribl</span>
              <span className={`text-xl font-bold ml-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Health Check
              </span>
            </Link>
          </div>
          <div className="flex items-center space-x-4">
            {navItems.map((item) => {
              const Icon = item.icon
              const active = isActive(item.path)
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    active
                      ? isDark
                        ? 'bg-blue-900/50 text-blue-400'
                        : 'bg-blue-50 text-blue-700'
                      : isDark
                        ? 'text-gray-300 hover:bg-gray-700 hover:text-white'
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <Icon className="h-5 w-5 mr-2" />
                  {item.label}
                </Link>
              )
            })}
            <button
              onClick={toggleTheme}
              className={`p-2 rounded-md transition-colors ${
                isDark
                  ? 'text-gray-300 hover:bg-gray-700 hover:text-white'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
              aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDark ? (
                <SunIcon className="h-5 w-5" />
              ) : (
                <MoonIcon className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}

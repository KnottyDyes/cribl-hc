import { Link, useLocation } from 'react-router-dom'
import {
  KeyIcon,
  BeakerIcon,
  DocumentChartBarIcon,
} from '@heroicons/react/24/outline'

export function Navbar() {
  const location = useLocation()

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path)
  }

  const navItems = [
    { path: '/credentials', label: 'Credentials', icon: KeyIcon },
    { path: '/analysis', label: 'Analysis', icon: BeakerIcon },
    { path: '/results', label: 'Results', icon: DocumentChartBarIcon },
  ]

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="flex items-center">
              <span className="text-xl font-bold text-blue-600">Cribl</span>
              <span className="text-xl font-bold text-gray-900 ml-1">Health Check</span>
            </Link>
          </div>
          <div className="flex space-x-4">
            {navItems.map((item) => {
              const Icon = item.icon
              const active = isActive(item.path)
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    active
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <Icon className="h-5 w-5 mr-2" />
                  {item.label}
                </Link>
              )
            })}
          </div>
        </div>
      </div>
    </nav>
  )
}

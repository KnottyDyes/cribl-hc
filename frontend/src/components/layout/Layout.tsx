import type { ReactNode } from 'react'
import { Navbar } from './Navbar'
import { useTheme } from '../../hooks/useTheme'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const { resolvedTheme } = useTheme()
  
  return (
    <div className={`min-h-screen transition-colors duration-200 ${
      resolvedTheme === 'dark' ? 'bg-gray-900' : 'bg-gray-50'
    }`}>
      <Navbar />
      <main>{children}</main>
    </div>
  )
}

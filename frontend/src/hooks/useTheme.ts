import { useContext } from 'react'
import { ThemeContext } from '../contexts/theme-context'
import type { ThemeContextValue } from '../contexts/theme-types'

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

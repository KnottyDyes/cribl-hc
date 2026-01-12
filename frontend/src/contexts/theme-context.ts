import { createContext } from 'react'
import type { ThemeContextValue } from './theme-types'

export const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

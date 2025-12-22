import { ReactNode, HTMLAttributes } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string
  subtitle?: string
  children: ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hoverable?: boolean
}

export function Card({
  title,
  subtitle,
  children,
  className = '',
  padding = 'md',
  hoverable = false,
  ...props
}: CardProps) {
  const baseStyles = 'bg-white rounded-lg shadow-md border border-gray-200'
  const hoverStyles = hoverable ? 'hover:shadow-lg transition-shadow duration-200' : ''

  const paddingStyles = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  }

  return (
    <div className={`${baseStyles} ${hoverStyles} ${className}`} {...props}>
      {(title || subtitle) && (
        <div className={`border-b border-gray-200 ${paddingStyles[padding]} pb-4`}>
          {title && (
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          )}
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
          )}
        </div>
      )}
      <div className={title || subtitle ? paddingStyles[padding] : paddingStyles[padding]}>
        {children}
      </div>
    </div>
  )
}

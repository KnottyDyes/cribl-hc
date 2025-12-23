interface SkeletonProps {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string | number
  height?: string | number
  animation?: 'pulse' | 'wave' | 'none'
}

/**
 * Skeleton loading component for placeholder content
 */
export function Skeleton({
  className = '',
  variant = 'text',
  width,
  height,
  animation = 'pulse',
}: SkeletonProps) {
  const baseStyles = 'bg-gray-200'

  const animations = {
    pulse: 'animate-pulse',
    wave: 'animate-shimmer',
    none: '',
  }

  const variants = {
    text: 'rounded h-4',
    circular: 'rounded-full',
    rectangular: 'rounded',
  }

  const styles: React.CSSProperties = {}
  if (width) styles.width = typeof width === 'number' ? `${width}px` : width
  if (height) styles.height = typeof height === 'number' ? `${height}px` : height

  return (
    <div
      className={`${baseStyles} ${variants[variant]} ${animations[animation]} ${className}`}
      style={styles}
    />
  )
}

/**
 * Skeleton for card loading state
 */
export function SkeletonCard() {
  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-4">
      <Skeleton variant="rectangular" height={24} width="60%" />
      <div className="space-y-2">
        <Skeleton variant="text" width="100%" />
        <Skeleton variant="text" width="90%" />
        <Skeleton variant="text" width="85%" />
      </div>
      <div className="flex gap-2 mt-4">
        <Skeleton variant="rectangular" height={36} width={100} />
        <Skeleton variant="rectangular" height={36} width={100} />
      </div>
    </div>
  )
}

/**
 * Skeleton for table loading state
 */
export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {/* Table Header */}
      <div className="flex gap-4 pb-3 border-b border-gray-200">
        <Skeleton variant="text" width={120} />
        <Skeleton variant="text" width={150} />
        <Skeleton variant="text" width={200} />
        <Skeleton variant="text" width={100} />
      </div>

      {/* Table Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 py-3">
          <Skeleton variant="text" width={120} />
          <Skeleton variant="text" width={150} />
          <Skeleton variant="text" width={200} />
          <Skeleton variant="text" width={100} />
        </div>
      ))}
    </div>
  )
}

/**
 * Skeleton for analysis card
 */
export function SkeletonAnalysisCard() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-3">
          <Skeleton variant="rectangular" height={28} width="40%" />
          <div className="flex gap-4">
            <Skeleton variant="text" width={100} />
            <Skeleton variant="text" width={120} />
          </div>
          <Skeleton variant="text" width="60%" />
        </div>
        <Skeleton variant="rectangular" height={36} width={120} />
      </div>
    </div>
  )
}

/**
 * Skeleton for findings card
 */
export function SkeletonFindingCard() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton variant="rectangular" height={24} width={80} />
        <Skeleton variant="text" width="50%" />
      </div>
      <Skeleton variant="text" width="90%" />
      <Skeleton variant="text" width="80%" />
      <div className="pt-2">
        <Skeleton variant="text" width={150} />
      </div>
    </div>
  )
}

/**
 * Skeleton for credential card
 */
export function SkeletonCredentialCard() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="space-y-2 flex-1">
          <Skeleton variant="rectangular" height={24} width="30%" />
          <Skeleton variant="text" width="60%" />
        </div>
        <Skeleton variant="circular" width={40} height={40} />
      </div>
      <div className="flex gap-2 mt-4">
        <Skeleton variant="rectangular" height={32} width={80} />
        <Skeleton variant="rectangular" height={32} width={80} />
        <Skeleton variant="rectangular" height={32} width={80} />
      </div>
    </div>
  )
}

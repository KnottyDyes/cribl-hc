import React, { useCallback, useRef } from 'react'
import { PhotoIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { Button } from '../common'

interface LogoUploadProps {
  label: string
  value?: string
  onChange: (file: File) => void
  onRemove: () => void
  loading?: boolean
  error?: string
}

export function LogoUpload({
  label,
  value,
  onChange,
  onRemove,
  loading,
  error,
}: LogoUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      onChange(file)
    }
  }

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      const file = e.dataTransfer.files?.[0]
      if (file && file.type.startsWith('image/')) {
        onChange(file)
      }
    },
    [onChange]
  )

  const handleClick = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
      </label>
      
      <div
        onDragOver={onDragOver}
        onDrop={onDrop}
        className={`relative flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-lg transition-colors ${
          error
            ? 'border-red-300 bg-red-50 dark:bg-red-900/10'
            : 'border-gray-300 bg-gray-50 dark:bg-gray-800 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'
        }`}
      >
        {value ? (
          <div className="relative group w-full h-full flex items-center justify-center p-4">
            <img
              src={value}
              alt="Logo Preview"
              className="max-w-full max-h-full object-contain"
            />
            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-lg">
              <div className="flex space-x-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={handleClick}
                  loading={loading}
                >
                  Change
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  size="sm"
                  onClick={onRemove}
                  loading={loading}
                >
                  <XMarkIcon className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={handleClick}
            disabled={loading}
            className="flex flex-col items-center justify-center space-y-2 w-full h-full"
          >
            <PhotoIcon className="w-10 h-10 text-gray-400" />
            <div className="text-sm text-gray-600 dark:text-gray-400">
              <span className="font-medium text-blue-600 hover:text-blue-500">
                Click to upload
              </span>{' '}
              or drag and drop
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-500">
              PNG, JPG, SVG up to 2MB
            </p>
          </button>
        )}
        
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept="image/*"
          onChange={handleFileChange}
        />
      </div>
      
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}

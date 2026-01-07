import { useBranding } from '../../hooks/useBranding'

export function BrandingPreview() {
  const { branding } = useBranding()

  return (
    <div className="p-6 border border-gray-200 dark:border-gray-700 rounded-lg">
      <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Live Preview
      </h4>

      <div className="space-y-6">
        <div>
          <h5 className="text-md font-medium text-gray-700 dark:text-gray-300 mb-2">
            Provider
          </h5>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Name: {branding.provider?.name || 'Not Set'}
          </p>
        </div>
        <div>
          <h5 className="text-md font-medium text-gray-700 dark:text-gray-300 mb-2">
            Client
          </h5>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Name: {branding.client?.name || 'Not Set'}
          </p>
        </div>
        <div>
          <h5 className="text-md font-medium text-gray-700 dark:text-gray-300 mb-2">
            Theme Colors (Light)
          </h5>
          <div className="flex space-x-4">
            <div className="w-8 h-8 rounded-full" style={{ backgroundColor: branding.theme.light.primary }}></div>
            <div className="w-8 h-8 rounded-full" style={{ backgroundColor: branding.theme.light.secondary }}></div>
            <div className="w-8 h-8 rounded-full" style={{ backgroundColor: branding.theme.light.accent }}></div>
          </div>
        </div>
      </div>
    </div>
  )
}
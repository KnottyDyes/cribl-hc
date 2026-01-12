import { useBranding } from '../../hooks/useBranding'

export function BrandingPreview() {
  const { branding } = useBranding()

  return (
    <div className="p-6 border border-gray-200 dark:border-gray-700 rounded-lg space-y-8 bg-white dark:bg-gray-800">
      <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Live Preview</h4>

      <div className="space-y-6">
        <div>
          <h5 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
            Provider Branding
          </h5>
          <div className="p-4 border border-gray-100 dark:border-gray-700 rounded-md space-y-3">
            {branding.provider?.logo_base64 ? (
              <div className="h-12 flex items-center">
                <img
                  src={branding.provider.logo_base64}
                  alt="Provider Logo"
                  className="max-h-full object-contain"
                />
              </div>
            ) : (
              <div className="h-12 flex items-center justify-center border-2 border-dashed border-gray-200 dark:border-gray-700 rounded text-xs text-gray-400">
                No Provider Logo
              </div>
            )}
            <div>
              <div className="font-bold text-gray-900 dark:text-gray-100">
                {branding.provider?.name || 'Organization Name'}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {branding.provider?.tagline || 'Organization Tagline'}
              </div>
            </div>
          </div>
        </div>

        <div>
          <h5 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
            Client Branding
          </h5>
          <div className="p-4 border border-gray-100 dark:border-gray-700 rounded-md space-y-3 bg-gray-50 dark:bg-gray-900/50">
            {branding.client?.logo_base64 ? (
              <div className="h-12 flex items-center">
                <img
                  src={branding.client.logo_base64}
                  alt="Client Logo"
                  className="max-h-full object-contain"
                />
              </div>
            ) : (
              <div className="h-12 flex items-center justify-center border-2 border-dashed border-gray-200 dark:border-gray-700 rounded text-xs text-gray-400">
                No Client Logo
              </div>
            )}
            <div className="font-semibold text-gray-800 dark:text-gray-200">
              {branding.client?.name || 'Client Name'}
            </div>
          </div>
        </div>

        <div>
          <h5 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
            Theme Preview
          </h5>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="text-xs text-center text-gray-400">Light</div>
              <div className="flex justify-center space-x-2">
                <div
                  className="w-6 h-6 rounded-full ring-2 ring-white dark:ring-gray-800 shadow-sm"
                  style={{ backgroundColor: branding.theme.light.primary }}
                  title="Primary"
                ></div>
                <div
                  className="w-6 h-6 rounded-full ring-2 ring-white dark:ring-gray-800 shadow-sm"
                  style={{ backgroundColor: branding.theme.light.secondary }}
                  title="Secondary"
                ></div>
                <div
                  className="w-6 h-6 rounded-full ring-2 ring-white dark:ring-gray-800 shadow-sm"
                  style={{ backgroundColor: branding.theme.light.accent }}
                  title="Accent"
                ></div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-xs text-center text-gray-400">Dark</div>
              <div className="flex justify-center space-x-2">
                <div
                  className="w-6 h-6 rounded-full ring-2 ring-white dark:ring-gray-800 shadow-sm"
                  style={{ backgroundColor: branding.theme.dark.primary }}
                  title="Primary"
                ></div>
                <div
                  className="w-6 h-6 rounded-full ring-2 ring-white dark:ring-gray-800 shadow-sm"
                  style={{ backgroundColor: branding.theme.dark.secondary }}
                  title="Secondary"
                ></div>
                <div
                  className="w-6 h-6 rounded-full ring-2 ring-white dark:ring-gray-800 shadow-sm"
                  style={{ backgroundColor: branding.theme.dark.accent }}
                  title="Accent"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
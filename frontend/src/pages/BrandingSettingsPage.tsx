import { useState } from 'react'
import { Card, Skeleton } from '../components/common'
import { ProviderBrandingForm } from '../components/branding/ProviderBrandingForm'
import { ClientBrandingForm } from '../components/branding/ClientBrandingForm'
import { ThemeColorsForm } from '../components/branding/ThemeColorsForm'
import { ReportStylingForm } from '../components/branding/ReportStylingForm'
import { useBranding } from '../hooks/useBranding'
import { BrandingPreview } from '../components/branding/BrandingPreview'

type Tab = 'provider' | 'client' | 'theme' | 'report'

export function BrandingSettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('provider')
  const { isLoading, error } = useBranding()

  const tabs = [
    { id: 'provider', label: 'Provider Branding' },
    { id: 'client', label: 'Client Branding' },
    { id: 'theme', label: 'Theme & Colors' },
    { id: 'report', label: 'Report Styling' },
  ] as const

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="space-y-4 p-6">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      )
    }

    if (error) {
      return (
        <div className="p-6 text-center text-red-500">
          Error loading branding configuration. Please try again.
        </div>
      )
    }

    switch (activeTab) {
      case 'provider':
        return <ProviderBrandingForm />
      case 'client':
        return <ClientBrandingForm />
      case 'theme':
        return <ThemeColorsForm />
      case 'report':
        return <ReportStylingForm />
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Branding Settings
          </h1>
          <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
            Customize the appearance of the application and generated reports.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-8">
             <Card>
                <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
                  <nav className="-mb-px flex space-x-8">
                    {tabs.map((tab) => (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => setActiveTab(tab.id)}
                        className={`whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                          activeTab === tab.id
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </nav>
                </div>
                {renderContent()}
              </Card>
          </div>

          <div className="lg:col-span-1">
            <div className="sticky top-24">
              <BrandingPreview />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
import { useEffect } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button, Input } from '../common'
import type { ReportBranding } from '../../api/types'
import { reportBrandingSchema } from '../../lib/validation'
import { useBranding } from '../../hooks/useBranding'

export function ReportStylingForm() {
  const { branding, updateBranding, isUpdating } = useBranding()

  const {
    register,
    handleSubmit,
    control,
    reset,
    watch,
    formState: { isDirty },
  } = useForm<ReportBranding>({
    resolver: zodResolver(reportBrandingSchema),
    defaultValues: branding.report,
  })

  const showWatermark = watch('show_watermark')

  useEffect(() => {
    reset(branding.report)
  }, [branding.report, reset])

  const onSubmit = (data: ReportBranding) => {
    updateBranding({ report: data })
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <Controller
          name="show_provider_logo"
          control={control}
          render={({ field }) => (
            <label className="flex items-center space-x-2">
              <input type="checkbox" {...field} checked={field.value} value={field.value.toString()} className="w-4 h-4 rounded" />
              <span>Show Provider Logo</span>
            </label>
          )}
        />
        <Controller
          name="show_client_logo"
          control={control}
          render={({ field }) => (
            <label className="flex items-center space-x-2">
              <input type="checkbox" {...field} checked={field.value} value={field.value.toString()} className="w-4 h-4 rounded" />
              <span>Show Client Logo</span>
            </label>
          )}
        />
        <Controller
          name="show_footer"
          control={control}
          render={({ field }) => (
            <label className="flex items-center space-x-2">
              <input type="checkbox" {...field} checked={field.value} value={field.value.toString()} className="w-4 h-4 rounded" />
              <span>Show Footer</span>
            </label>
          )}
        />
        <Controller
          name="show_watermark"
          control={control}
          render={({ field }) => (
            <label className="flex items-center space-x-2">
              <input type="checkbox" {...field} checked={field.value} value={field.value.toString()} className="w-4 h-4 rounded" />
              <span>Enable Watermark</span>
            </label>
          )}
        />
      </div>

      {showWatermark && (
        <Input
          label="Watermark Text"
          placeholder="e.g., CONFIDENTIAL"
          {...register('watermark_text')}
        />
      )}

      <div className="pt-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Custom CSS
        </label>
        <textarea
          {...register('custom_css')}
          rows={6}
          className="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm font-mono"
          placeholder="/* Custom CSS to inject into reports */"
        />
      </div>

      <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <Button type="submit" loading={isUpdating} disabled={!isDirty || isUpdating}>
          Save Report Styling
        </Button>
      </div>
    </form>
  )
}
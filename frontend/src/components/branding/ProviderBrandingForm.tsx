import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button, Input } from '../common'
import type { ServiceProviderBranding } from '../../api/types'
import { serviceProviderBrandingSchema } from '../../lib/validation'
import { useBranding } from '../../hooks/useBranding'

export function ProviderBrandingForm() {
  const { branding, updateProvider, deleteProvider, isUpdatingProvider, isDeletingProvider } = useBranding()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<ServiceProviderBranding>({
    resolver: zodResolver(serviceProviderBrandingSchema),
    defaultValues: branding.provider || {
      name: '',
      contact_email: '',
      website: '',
      tagline: '',
      footer_text: '',
    },
  })

  useEffect(() => {
    reset(branding.provider || {
      name: '',
      contact_email: '',
      website: '',
      tagline: '',
      footer_text: '',
    })
  }, [branding.provider, reset])

  const onSubmit = (data: ServiceProviderBranding) => {
    updateProvider(data)
  }

  const handleDelete = () => {
    if (confirm('Are you sure you want to remove provider branding?')) {
      deleteProvider()
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Input
          label="Organization Name"
          {...register('name')}
          error={errors.name?.message}
          required
        />
        <Input
          label="Contact Email"
          type="email"
          {...register('contact_email')}
          error={errors.contact_email?.message}
        />
        <Input
          label="Website"
          type="url"
          placeholder="https://example.com"
          {...register('website')}
          error={errors.website?.message}
        />
        <Input
          label="Tagline"
          placeholder="Your company tagline"
          {...register('tagline')}
          error={errors.tagline?.message}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Report Footer Text
        </label>
        <textarea
          {...register('footer_text')}
          rows={3}
          className="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          placeholder="Legal disclaimer or copyright notice"
        />
        {errors.footer_text && <p className="mt-1 text-sm text-red-600">{errors.footer_text.message}</p>}
      </div>

      <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        {branding.provider && (
          <Button
            type="button"
            variant="danger"
            onClick={handleDelete}
            loading={isDeletingProvider}
          >
            Remove
          </Button>
        )}
        <Button type="submit" loading={isUpdatingProvider} disabled={!isDirty || isUpdatingProvider}>
          Save Changes
        </Button>
      </div>
    </form>
  )
}
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button, Input } from '../common'
import type { ClientBranding } from '../../api/types'
import { clientBrandingSchema } from '../../lib/validation'
import { useBranding } from '../../hooks/useBranding'
import { LogoUpload } from './LogoUpload'

export function ClientBrandingForm() {
  const {
    branding,
    updateClient,
    deleteClient,
    uploadLogo,
    deleteLogo,
    isUpdatingClient,
    isDeletingClient,
    isUploadingLogo,
    isDeletingLogo,
  } = useBranding()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<ClientBranding>({
    resolver: zodResolver(clientBrandingSchema),
    defaultValues: branding.client || {
      name: '',
      identifier: '',
      report_title: '',
    },
  })

  useEffect(() => {
    reset(
      branding.client || {
        name: '',
        identifier: '',
        report_title: '',
      }
    )
  }, [branding.client, reset])

  const onSubmit = (data: ClientBranding) => {
    updateClient(data)
  }

  const handleDelete = () => {
    if (confirm('Are you sure you want to remove client branding?')) {
      deleteClient()
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="space-y-6">
          <Input label="Client Name" {...register('name')} error={errors.name?.message} required />
          <Input
            label="Client Identifier"
            placeholder="Account number or reference code"
            {...register('identifier')}
            error={errors.identifier?.message}
          />
          <Input
            label="Custom Report Title"
            placeholder="Overrides the default report title"
            {...register('report_title')}
            error={errors.report_title?.message}
          />
        </div>

        <div className="space-y-6">
          <LogoUpload
            label="Client Logo"
            value={branding.client?.logo_base64}
            onChange={(file) => uploadLogo('client', file)}
            onRemove={() => deleteLogo('client')}
            loading={isUploadingLogo || isDeletingLogo}
          />
          <LogoUpload
            label="Client Dark Logo (Optional)"
            value={branding.client?.logo_dark_base64}
            onChange={(file) => uploadLogo('client_dark', file)}
            onRemove={() => deleteLogo('client_dark')}
            loading={isUploadingLogo || isDeletingLogo}
          />
        </div>
      </div>

      <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        {branding.client && (
          <Button type="button" variant="danger" onClick={handleDelete} loading={isDeletingClient}>
            Remove
          </Button>
        )}
        <Button type="submit" loading={isUpdatingClient} disabled={!isDirty || isUpdatingClient}>
          Save Changes
        </Button>
      </div>
    </form>
  )
}
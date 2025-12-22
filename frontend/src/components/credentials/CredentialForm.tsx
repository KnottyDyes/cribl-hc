import { useState } from 'react'
import { Input, Select, Button } from '../common'
import type { CredentialCreate, AuthType } from '../../api/types'

interface CredentialFormProps {
  onSubmit: (data: CredentialCreate) => void
  onCancel: () => void
  initialData?: Partial<CredentialCreate>
  isSubmitting?: boolean
}

export function CredentialForm({
  onSubmit,
  onCancel,
  initialData,
  isSubmitting = false,
}: CredentialFormProps) {
  const [formData, setFormData] = useState<CredentialCreate>({
    name: initialData?.name || '',
    url: initialData?.url || '',
    auth_type: initialData?.auth_type || 'bearer',
    token: initialData?.token || '',
    client_id: initialData?.client_id || '',
    client_secret: initialData?.client_secret || '',
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required'
    }

    if (!formData.url.trim()) {
      newErrors.url = 'URL is required'
    } else {
      try {
        new URL(formData.url)
      } catch {
        newErrors.url = 'Must be a valid URL'
      }
    }

    if (formData.auth_type === 'bearer' && !formData.token?.trim()) {
      newErrors.token = 'Token is required for bearer authentication'
    }

    if (formData.auth_type === 'oauth') {
      if (!formData.client_id?.trim()) {
        newErrors.client_id = 'Client ID is required for OAuth'
      }
      if (!formData.client_secret?.trim()) {
        newErrors.client_secret = 'Client Secret is required for OAuth'
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validate()) {
      onSubmit(formData)
    }
  }

  const authTypeOptions = [
    { value: 'bearer', label: 'Bearer Token' },
    { value: 'oauth', label: 'OAuth 2.0' },
  ]

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label="Credential Name"
        value={formData.name}
        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
        error={errors.name}
        placeholder="my-cribl-deployment"
        required
        disabled={!!initialData?.name}
      />

      <Input
        label="Cribl URL"
        type="url"
        value={formData.url}
        onChange={(e) => setFormData({ ...formData, url: e.target.value })}
        error={errors.url}
        placeholder="https://cribl.example.com"
        helperText="Full URL to your Cribl deployment"
        required
      />

      <Select
        label="Authentication Type"
        value={formData.auth_type}
        onChange={(e) =>
          setFormData({ ...formData, auth_type: e.target.value as AuthType })
        }
        options={authTypeOptions}
        required
      />

      {formData.auth_type === 'bearer' && (
        <Input
          label="Bearer Token"
          type="password"
          value={formData.token || ''}
          onChange={(e) => setFormData({ ...formData, token: e.target.value })}
          error={errors.token}
          placeholder="Enter your bearer token"
          helperText="API token from Cribl deployment"
          required
        />
      )}

      {formData.auth_type === 'oauth' && (
        <>
          <Input
            label="Client ID"
            value={formData.client_id || ''}
            onChange={(e) =>
              setFormData({ ...formData, client_id: e.target.value })
            }
            error={errors.client_id}
            placeholder="oauth-client-id"
            required
          />
          <Input
            label="Client Secret"
            type="password"
            value={formData.client_secret || ''}
            onChange={(e) =>
              setFormData({ ...formData, client_secret: e.target.value })
            }
            error={errors.client_secret}
            placeholder="Enter client secret"
            required
          />
        </>
      )}

      <div className="flex justify-end gap-3 pt-4">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={isSubmitting}>
          {initialData ? 'Update Credential' : 'Add Credential'}
        </Button>
      </div>
    </form>
  )
}

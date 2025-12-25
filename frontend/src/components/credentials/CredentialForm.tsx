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

  /**
   * Extract URL and token from pasted content
   * Handles:
   * - curl commands: curl -H "Authorization: Bearer TOKEN" https://example.com/api/v1/...
   * - Raw URLs: https://example.com/api/v1/something
   * - URLs with paths (strips to base URL)
   */
  const extractFromPaste = (text: string): { url?: string; token?: string } => {
    const result: { url?: string; token?: string } = {}

    // Extract Bearer token from curl command or Authorization header
    const bearerMatch = text.match(/(?:Bearer\s+|bearer\s+)([A-Za-z0-9_\-.]+)/i)
    if (bearerMatch) {
      result.token = bearerMatch[1]
    }

    // Extract URL (handles both curl and raw URLs)
    const urlMatch = text.match(/(https?:\/\/[^\s"'<>]+)/i)
    if (urlMatch) {
      const url = urlMatch[1]

      // Strip API path - keep only base URL
      // Example: https://cribl.example.com/api/v1/system/status -> https://cribl.example.com
      try {
        const urlObj = new URL(url)
        result.url = `${urlObj.protocol}//${urlObj.host}`
      } catch {
        // If URL parsing fails, use as-is
        result.url = url
      }
    }

    return result
  }

  const handleUrlPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const pastedText = e.clipboardData.getData('text')
    const extracted = extractFromPaste(pastedText)

    if (extracted.url || extracted.token) {
      e.preventDefault() // Prevent default paste

      setFormData((prev) => ({
        ...prev,
        ...(extracted.url && { url: extracted.url }),
        ...(extracted.token && { token: extracted.token, auth_type: 'bearer' }),
      }))
    }
  }

  const handleTokenPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const pastedText = e.clipboardData.getData('text')
    const extracted = extractFromPaste(pastedText)

    if (extracted.token || extracted.url) {
      e.preventDefault() // Prevent default paste

      setFormData((prev) => ({
        ...prev,
        ...(extracted.token && { token: extracted.token }),
        ...(extracted.url && { url: extracted.url }),
      }))
    }
  }

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
        onPaste={handleUrlPaste}
        error={errors.url}
        placeholder="https://cribl.example.com"
        helperText="Paste a curl command or API URL - we'll extract the base URL and token"
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
          onPaste={handleTokenPaste}
          error={errors.token}
          placeholder="Enter your bearer token"
          helperText="Paste a curl command or bearer token - we'll extract it automatically"
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

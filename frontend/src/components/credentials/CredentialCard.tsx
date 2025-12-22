import type { Credential } from '../../api/types'
import { Card } from '../common'
import { TrashIcon, PencilIcon, WifiIcon } from '@heroicons/react/24/outline'
import { Button } from '../common'

interface CredentialCardProps {
  credential: Credential
  onEdit: (credential: Credential) => void
  onDelete: (name: string) => void
  onTest: (name: string) => void
  testing?: boolean
}

export function CredentialCard({
  credential,
  onEdit,
  onDelete,
  onTest,
  testing = false,
}: CredentialCardProps) {
  return (
    <Card hoverable className="transition-all">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h4 className="text-lg font-semibold text-gray-900">{credential.name}</h4>
          <p className="mt-1 text-sm text-gray-500">{credential.url}</p>
          <div className="mt-2 flex items-center gap-3">
            <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
              {credential.auth_type.toUpperCase()}
            </span>
            {credential.has_token && (
              <span className="text-xs text-gray-500">Token configured</span>
            )}
            {credential.has_oauth && (
              <span className="text-xs text-gray-500">OAuth configured</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onTest(credential.name)}
            loading={testing}
            title="Test connection"
          >
            <WifiIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(credential)}
            title="Edit credential"
          >
            <PencilIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(credential.name)}
            title="Delete credential"
          >
            <TrashIcon className="h-4 w-4 text-red-600" />
          </Button>
        </div>
      </div>
    </Card>
  )
}

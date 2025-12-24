import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { credentialsApi } from '../../api/credentials'
import { CredentialCard } from './CredentialCard'
import { CredentialForm } from './CredentialForm'
import { Button, Modal } from '../common'
import { PlusIcon } from '@heroicons/react/24/outline'
import type { Credential, CredentialCreate } from '../../api/types'

export function CredentialList() {
  const queryClient = useQueryClient()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingCredential, setEditingCredential] = useState<Credential | null>(null)
  const [testingCredential, setTestingCredential] = useState<string | null>(null)

  const { data: credentials, isLoading } = useQuery({
    queryKey: ['credentials'],
    queryFn: credentialsApi.list,
  })

  const createMutation = useMutation({
    mutationFn: credentialsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
      setIsModalOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ name, data }: { name: string; data: CredentialCreate }) =>
      credentialsApi.update(name, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
      setIsModalOpen(false)
      setEditingCredential(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: credentialsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
    },
  })

  const testMutation = useMutation({
    mutationFn: credentialsApi.test,
    onSuccess: (result) => {
      setTestingCredential(null)
      if (result.success) {
        alert(`Connection successful!\n${result.message}`)
      } else {
        alert(`Connection failed!\n${result.message}`)
      }
    },
    onError: () => {
      setTestingCredential(null)
      alert('Connection test failed!')
    },
  })

  const handleCreate = (data: CredentialCreate) => {
    createMutation.mutate(data)
  }

  const handleUpdate = (data: CredentialCreate) => {
    if (editingCredential) {
      updateMutation.mutate({ name: editingCredential.name, data })
    }
  }

  const handleDelete = (name: string) => {
    if (confirm(`Are you sure you want to delete credential "${name}"?`)) {
      deleteMutation.mutate(name)
    }
  }

  const handleTest = (name: string) => {
    setTestingCredential(name)
    testMutation.mutate(name)
  }

  const handleEdit = (credential: Credential) => {
    setEditingCredential(credential)
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setEditingCredential(null)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Credentials</h2>
          <p className="mt-1 text-sm text-gray-500">
            Manage your Cribl deployment credentials
          </p>
        </div>
        <Button onClick={() => setIsModalOpen(true)}>
          <PlusIcon className="h-5 w-5 mr-2" />
          Add Credential
        </Button>
      </div>

      {credentials && credentials.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No credentials configured yet.</p>
          <Button className="mt-4" onClick={() => setIsModalOpen(true)}>
            Add Your First Credential
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {credentials?.map((credential) => (
            <CredentialCard
              key={credential.name}
              credential={credential}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onTest={handleTest}
              testing={testingCredential === credential.name}
            />
          ))}
        </div>
      )}

      <Modal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        title={editingCredential ? 'Edit Credential' : 'Add New Credential'}
        size="lg"
      >
        <CredentialForm
          onSubmit={editingCredential ? handleUpdate : handleCreate}
          onCancel={handleCloseModal}
          initialData={editingCredential || undefined}
          isSubmitting={createMutation.isPending || updateMutation.isPending}
        />
      </Modal>
    </div>
  )
}

// Test file to verify types are exported correctly
import type { Credential } from './api/types'

const testCredential: Credential = {
  name: 'test',
  url: 'https://example.com',
  auth_type: 'bearer',
  has_token: true,
  has_oauth: false,
}

console.log('Types loaded successfully:', testCredential)

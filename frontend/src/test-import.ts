// Test import
import { Credential } from './api/types'

console.log('Import successful!')

const test: Credential = {
  name: 'test',
  url: 'http://test.com',
  auth_type: 'bearer',
  has_token: true,
  has_oauth: false,
}

console.log(test)

# OAuth Authentication Support - Implementation Summary

**Date**: 2025-12-18
**Feature**: Dual Authentication Support (Bearer Token + OAuth Client Credentials)

## Overview

Enhanced cribl-hc to support **both** authentication methods for Cribl Stream API:

1. **Bearer Token** (existing) - Direct token from API Reference menu
2. **OAuth Client Credentials** (NEW) - Client ID/Secret pairs from Settings → API Settings

This addresses the real-world scenario where admins create API Key/Secret pairs instead of using bearer tokens.

## Implementation

### 1. Credential Storage Enhancement

**File**: [src/cribl_hc/cli/commands/config.py](src/cribl_hc/cli/commands/config.py)

**Changes**:
- Updated `set_credential()` command to accept both auth methods
- Added `--client-id` and `--client-secret` options
- Store `auth_type` field ('bearer' or 'oauth') in credentials
- Updated `get_credential()` and `list_credentials()` to display auth type
- Created `create_api_client_from_credentials()` helper function

**Credential Format**:
```json
{
  "prod": {
    "url": "https://main-myorg.cribl.cloud",
    "auth_type": "oauth",
    "client_id": "abc123...",
    "client_secret": "xyz789..."
  },
  "dev": {
    "url": "https://cribl.example.com",
    "auth_type": "bearer",
    "token": "eyJ0eXAi..."
  }
}
```

### 2. OAuth Token Manager

**File**: [src/cribl_hc/core/auth.py](src/cribl_hc/core/auth.py) (NEW)

**Features**:
- `OAuthTokenManager` class handles OAuth 2.0 client credentials flow
- Exchanges Client ID/Secret for Bearer token via `https://login.cribl.cloud/oauth/token`
- Token caching with expiration tracking (24 hour tokens)
- Automatic token refresh with 5-minute safety buffer
- Proper error handling and logging

**OAuth Flow**:
```
1. Client provides client_id + client_secret
2. POST to https://login.cribl.cloud/oauth/token
   Body: {
     "grant_type": "client_credentials",
     "client_id": "...",
     "client_secret": "...",
     "audience": "https://api.cribl.cloud"
   }
3. Receive access_token (JWT) valid for 24 hours
4. Use access_token as Bearer token for API calls
```

### 3. API Client Updates

**File**: [src/cribl_hc/core/api_client.py](src/cribl_hc/core/api_client.py)

**Changes**:
- Updated `__init__()` to accept either:
  - `auth_token` (direct bearer token), OR
  - `client_id` + `client_secret` (OAuth)
- Added `_oauth_manager` to handle OAuth token lifecycle
- Updated `__aenter__()` to get OAuth token before creating HTTP client
- Backward compatible: existing code using `auth_token` continues to work

**Usage**:
```python
# Method 1: Bearer Token (existing)
client = CriblAPIClient(
    base_url="https://cribl.example.com",
    auth_token="your_bearer_token"
)

# Method 2: OAuth Client Credentials (NEW)
client = CriblAPIClient(
    base_url="https://main-myorg.cribl.cloud",
    client_id="your_client_id",
    client_secret="your_client_secret"
)
```

### 4. CLI Command Updates

**Commands Updated**:

#### `cribl-hc config set`
```bash
# Bearer Token (existing method)
cribl-hc config set prod --url https://cribl.example.com --token YOUR_TOKEN

# OAuth Client Credentials (NEW method)
cribl-hc config set prod --url https://main-myorg.cribl.cloud \\
  --client-id abc123 --client-secret xyz789
```

#### `cribl-hc config get`
```bash
$ cribl-hc config get prod
Credentials for: prod
URL: https://main-myorg.cribl.cloud
Auth Type: OAuth
Client ID: abc123
Client Secret: ****************************************
```

#### `cribl-hc config list`
```
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name ┃ URL                        ┃ Auth Type ┃ Credential           ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ prod │ https://main-myorg.cribl.c │ Oauth     │ Client ID: abc123... │
│ dev  │ https://cribl.example.com  │ Bearer    │ ********************  │
└──────┴────────────────────────────┴───────────┴──────────────────────┘
```

### 5. Helper Functions

**File**: [src/cribl_hc/cli/commands/__init__.py](src/cribl_hc/cli/commands/__init__.py)

**Exported Functions**:
- `create_api_client_from_credentials(deployment_name)` - Creates API client from stored creds
- `load_credentials()` - Load encrypted credentials
- `save_credentials(credentials)` - Save encrypted credentials

## Files Modified

### Created
1. `src/cribl_hc/core/auth.py` (128 lines) - OAuth token manager
2. `OAUTH_AUTHENTICATION_SUPPORT.md` (this file)

### Modified
1. `src/cribl_hc/cli/commands/config.py` - Enhanced credential management
2. `src/cribl_hc/core/api_client.py` - Added OAuth support
3. `src/cribl_hc/cli/commands/__init__.py` - Exported helper functions

### TODO (Remaining Work)
- [ ] Update TUI to support API key/secret input
- [ ] Add unit tests for OAuth authentication
- [ ] Add integration tests with mock OAuth endpoint
- [ ] Update README with OAuth examples
- [ ] Update CLI_GUIDE.md with OAuth documentation

## Backward Compatibility

✅ **100% Backward Compatible**

- Existing credentials with bearer tokens continue to work
- No breaking changes to API client interface
- Default `auth_type` is 'bearer' for legacy credentials
- All existing code paths remain functional

## Security Considerations

1. **Credential Encryption**: Both token and client_id/client_secret are encrypted at rest
2. **Token Caching**: OAuth tokens cached in memory only (not persisted)
3. **Token Expiration**: Automatic refresh with safety buffer prevents token expiry during operations
4. **Least Privilege**: OAuth tokens have same permissions as the API credential that created them
5. **Audit Trail**: All OAuth token requests logged via structlog

## Testing

### Manual Testing

```bash
# Test OAuth authentication
cribl-hc config set test-oauth \\
  --url https://main-myorg.cribl.cloud \\
  --client-id YOUR_CLIENT_ID \\
  --client-secret YOUR_CLIENT_SECRET

# Verify credential storage
cribl-hc config get test-oauth

# Test connection (will trigger OAuth flow)
cribl-hc test-connection test-oauth

# Run analysis (uses OAuth token)
cribl-hc analyze health --deployment test-oauth
```

### Unit Tests (TODO)

```python
# tests/unit/test_core/test_auth.py
async def test_oauth_token_exchange():
    """Test OAuth token exchange with mock endpoint."""
    manager = OAuthTokenManager("test_id", "test_secret")
    # Mock httpx response...
    token = await manager.get_access_token()
    assert token.startswith("eyJ")

async def test_oauth_token_caching():
    """Test that tokens are cached until expiration."""
    # Verify only one token request for multiple calls...

async def test_oauth_token_refresh():
    """Test automatic token refresh on expiration."""
    # Mock time progression...
```

## Documentation

### User-Facing

**How to Get OAuth Credentials**:
1. Log into Cribl.Cloud as Owner/Admin
2. Navigate to **Products** → **Cribl** → **Organization** → **API Credentials**
3. Click **Create API Credential**
4. Copy the Client ID and Client Secret
5. Store using: `cribl-hc config set DEPLOYMENT --url URL --client-id ID --client-secret SECRET`

**When to Use Each Method**:
- **Bearer Token**: Quick testing, personal use, on-prem deployments
- **OAuth Credentials**: Production use, Cribl.Cloud, automated workflows, credential rotation

### Technical Details

**OAuth Endpoint**: `https://login.cribl.cloud/oauth/token`

**Token Lifetime**: 24 hours (86400 seconds)

**Audience**: `https://api.cribl.cloud`

**Grant Type**: `client_credentials`

## Benefits

1. **Admin Preferred**: Admins can use API credentials they're already creating
2. **Better Security**: OAuth tokens auto-expire, support credential rotation
3. **Cribl.Cloud Ready**: OAuth is the recommended method for Cribl.Cloud
4. **Flexible**: Users can choose authentication method that fits their workflow
5. **Future Proof**: Aligns with Cribl's authentication roadmap

## Known Limitations

1. **Cribl.Cloud Only**: OAuth endpoint is Cribl.Cloud specific
   - On-prem deployments should continue using bearer tokens
2. **Token Lifespan**: 24-hour tokens may expire during long-running operations
   - Mitigated by automatic refresh logic
3. **No Token Revocation**: Cached tokens aren't immediately invalidated if credentials change
   - Restart cribl-hc or wait for token expiration

## Future Enhancements

1. **Token Refresh**: Implement refresh token flow (if Cribl supports it)
2. **PKCE Flow**: Add browser-based OAuth for user tokens
3. **SSO Integration**: Support SAML/OIDC for enterprise auth
4. **Token Introspection**: Validate token permissions before use
5. **Multi-Tenancy**: Support multiple Cribl organizations

## References

- [Cribl API Authentication Docs](https://docs.cribl.io/cribl-as-code/api-auth/)
- [Cribl Manage Secrets](https://docs.cribl.io/stream/manage-secrets-and-keys/)
- [OAuth 2.0 Client Credentials Grant](https://oauth.net/2/grant-types/client-credentials/)

---

**Status**: Core implementation complete, TUI and tests pending
**Impact**: Medium (enables new authentication workflow, maintains backward compatibility)
**Risk**: Low (isolated changes, no breaking changes)

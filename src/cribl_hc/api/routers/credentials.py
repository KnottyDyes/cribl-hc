"""
Credential management API endpoints.

Provides CRUD operations for deployment credentials with support for
both Bearer Token and OAuth authentication methods.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from cribl_hc.cli.commands.config import (
    load_credentials,
    save_credentials,
)
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)


class CredentialCreate(BaseModel):
    """Request model for creating credentials."""
    name: str = Field(..., description="Deployment identifier")
    url: str = Field(..., description="Cribl Stream API URL")
    auth_type: str = Field(..., description="Authentication type: 'bearer' or 'oauth'")

    # Bearer token fields
    token: Optional[str] = Field(None, description="Bearer token (for auth_type='bearer')")

    # OAuth fields
    client_id: Optional[str] = Field(None, description="OAuth client ID (for auth_type='oauth')")
    client_secret: Optional[str] = Field(None, description="OAuth client secret (for auth_type='oauth')")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "prod",
                "url": "https://main-myorg.cribl.cloud",
                "auth_type": "oauth",
                "client_id": "your_client_id",
                "client_secret": "your_client_secret"
            }
        }


class CredentialUpdate(BaseModel):
    """Request model for updating credentials."""
    url: Optional[str] = Field(None, description="Cribl Stream API URL")
    auth_type: Optional[str] = Field(None, description="Authentication type")
    token: Optional[str] = Field(None, description="Bearer token")
    client_id: Optional[str] = Field(None, description="OAuth client ID")
    client_secret: Optional[str] = Field(None, description="OAuth client secret")


class CredentialResponse(BaseModel):
    """Response model for credential data (masked secrets)."""
    name: str
    url: str
    auth_type: str
    has_token: bool = Field(description="Whether bearer token is configured")
    has_oauth: bool = Field(description="Whether OAuth credentials are configured")
    client_id: Optional[str] = Field(None, description="OAuth client ID (not secret)")


class ConnectionTestResult(BaseModel):
    """Result of connection test."""
    success: bool
    message: str
    cribl_version: Optional[str] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None


@router.get("", response_model=List[CredentialResponse])
async def list_credentials():
    """
    List all configured credentials.

    Returns basic info for each credential with secrets masked.
    """
    try:
        credentials = load_credentials()

        response = []
        for name, cred in credentials.items():
            auth_type = cred.get("auth_type", "bearer")

            response.append(CredentialResponse(
                name=name,
                url=cred["url"],
                auth_type=auth_type,
                has_token="token" in cred,
                has_oauth="client_id" in cred and "client_secret" in cred,
                client_id=cred.get("client_id") if auth_type == "oauth" else None,
            ))

        return response

    except Exception as e:
        log.error("list_credentials_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list credentials: {str(e)}"
        )


@router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_credential(credential: CredentialCreate):
    """
    Create new deployment credentials.

    Validates authentication method and required fields.
    """
    try:
        credentials = load_credentials()

        # Check if already exists
        if credential.name in credentials:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Credential '{credential.name}' already exists"
            )

        # Validate auth method
        if credential.auth_type == "bearer":
            if not credential.token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bearer token is required for auth_type='bearer'"
                )
            new_cred = {
                "url": credential.url,
                "auth_type": "bearer",
                "token": credential.token,
            }

        elif credential.auth_type == "oauth":
            if not credential.client_id or not credential.client_secret:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Both client_id and client_secret are required for auth_type='oauth'"
                )
            new_cred = {
                "url": credential.url,
                "auth_type": "oauth",
                "client_id": credential.client_id,
                "client_secret": credential.client_secret,
            }

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid auth_type: {credential.auth_type}. Must be 'bearer' or 'oauth'"
            )

        # Save credentials
        credentials[credential.name] = new_cred
        save_credentials(credentials)

        log.info("credential_created", name=credential.name, auth_type=credential.auth_type)

        return CredentialResponse(
            name=credential.name,
            url=new_cred["url"],
            auth_type=new_cred["auth_type"],
            has_token="token" in new_cred,
            has_oauth="client_id" in new_cred,
            client_id=new_cred.get("client_id"),
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("create_credential_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create credential: {str(e)}"
        )


@router.get("/{name}", response_model=CredentialResponse)
async def get_credential(name: str):
    """
    Get details for a specific credential.

    Secrets are masked in the response.
    """
    try:
        credentials = load_credentials()

        if name not in credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credential '{name}' not found"
            )

        cred = credentials[name]
        auth_type = cred.get("auth_type", "bearer")

        return CredentialResponse(
            name=name,
            url=cred["url"],
            auth_type=auth_type,
            has_token="token" in cred,
            has_oauth="client_id" in cred and "client_secret" in cred,
            client_id=cred.get("client_id") if auth_type == "oauth" else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("get_credential_error", name=name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get credential: {str(e)}"
        )


@router.put("/{name}", response_model=CredentialResponse)
async def update_credential(name: str, updates: CredentialUpdate):
    """
    Update existing credential.

    Only provided fields are updated.
    """
    try:
        credentials = load_credentials()

        if name not in credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credential '{name}' not found"
            )

        cred = credentials[name]

        # Update fields
        if updates.url is not None:
            cred["url"] = updates.url

        if updates.auth_type is not None:
            cred["auth_type"] = updates.auth_type

        if updates.token is not None:
            cred["token"] = updates.token
            cred["auth_type"] = "bearer"

        if updates.client_id is not None:
            cred["client_id"] = updates.client_id

        if updates.client_secret is not None:
            cred["client_secret"] = updates.client_secret

        # If OAuth credentials provided, update auth_type
        if updates.client_id and updates.client_secret:
            cred["auth_type"] = "oauth"

        credentials[name] = cred
        save_credentials(credentials)

        log.info("credential_updated", name=name)

        return CredentialResponse(
            name=name,
            url=cred["url"],
            auth_type=cred.get("auth_type", "bearer"),
            has_token="token" in cred,
            has_oauth="client_id" in cred and "client_secret" in cred,
            client_id=cred.get("client_id"),
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("update_credential_error", name=name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update credential: {str(e)}"
        )


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(name: str):
    """
    Delete a credential.

    Returns 204 No Content on success.
    """
    try:
        credentials = load_credentials()

        if name not in credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credential '{name}' not found"
            )

        del credentials[name]
        save_credentials(credentials)

        log.info("credential_deleted", name=name)

        return None

    except HTTPException:
        raise
    except Exception as e:
        log.error("delete_credential_error", name=name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete credential: {str(e)}"
        )


@router.post("/{name}/test", response_model=ConnectionTestResult)
async def test_connection(name: str):
    """
    Test connection to Cribl deployment.

    Validates credentials and checks API connectivity.
    """
    try:
        credentials = load_credentials()

        if name not in credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credential '{name}' not found"
            )

        cred = credentials[name]
        auth_type = cred.get("auth_type", "bearer")

        # Create API client
        if auth_type == "oauth":
            client = CriblAPIClient(
                base_url=cred["url"],
                client_id=cred["client_id"],
                client_secret=cred["client_secret"],
            )
        else:
            client = CriblAPIClient(
                base_url=cred["url"],
                auth_token=cred["token"],
            )

        # Test connection
        async with client:
            result = await client.test_connection()

        return ConnectionTestResult(
            success=result.success,
            message=result.message,
            cribl_version=result.cribl_version,
            response_time_ms=result.response_time_ms,
            error=result.error,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("test_connection_error", name=name, error=str(e))
        return ConnectionTestResult(
            success=False,
            message="Connection test failed",
            error=str(e),
        )

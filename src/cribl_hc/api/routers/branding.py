"""Branding API endpoints for theme and customization settings."""

import base64
import io
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from cribl_hc.core.branding_manager import get_branding_manager
from cribl_hc.models.branding import (
    BrandingConfig,
    ClientBranding,
    ReportBranding,
    ServiceProviderBranding,
    ThemeColors,
    ThemeMode,
    UITheme,
)

router = APIRouter()


class ThemeColorsUpdate(BaseModel):
    primary: Optional[str] = None
    primary_hover: Optional[str] = None
    primary_foreground: Optional[str] = None
    secondary: Optional[str] = None
    secondary_hover: Optional[str] = None
    secondary_foreground: Optional[str] = None
    accent: Optional[str] = None
    accent_hover: Optional[str] = None
    accent_foreground: Optional[str] = None
    background: Optional[str] = None
    background_secondary: Optional[str] = None
    background_tertiary: Optional[str] = None
    foreground: Optional[str] = None
    foreground_secondary: Optional[str] = None
    foreground_muted: Optional[str] = None
    border: Optional[str] = None
    border_focus: Optional[str] = None
    severity_critical: Optional[str] = None
    severity_high: Optional[str] = None
    severity_medium: Optional[str] = None
    severity_low: Optional[str] = None
    severity_info: Optional[str] = None
    success: Optional[str] = None
    warning: Optional[str] = None
    error: Optional[str] = None


class BrandingUpdateRequest(BaseModel):
    provider: Optional[ServiceProviderBranding] = None
    client: Optional[ClientBranding] = None
    theme: Optional[UITheme] = None
    report: Optional[ReportBranding] = None


class ThemeModeRequest(BaseModel):
    mode: ThemeMode


@router.get("", response_model=BrandingConfig)
async def get_branding():
    """Get current branding configuration."""
    manager = get_branding_manager()
    return manager.load()


@router.put("", response_model=BrandingConfig)
async def update_branding(request: BrandingUpdateRequest):
    """Update branding configuration (partial update supported)."""
    manager = get_branding_manager()
    current = manager.load()

    update_data = current.model_dump()

    if request.provider is not None:
        update_data["provider"] = request.provider.model_dump()
    if request.client is not None:
        update_data["client"] = request.client.model_dump()
    if request.theme is not None:
        update_data["theme"] = request.theme.model_dump()
    if request.report is not None:
        update_data["report"] = request.report.model_dump()

    updated = BrandingConfig.model_validate(update_data)
    manager.save(updated)
    return updated


@router.post("/reset", response_model=BrandingConfig)
async def reset_branding():
    """Reset branding to default values."""
    manager = get_branding_manager()
    return manager.reset()


@router.get("/theme", response_model=UITheme)
async def get_theme():
    """Get current UI theme settings."""
    manager = get_branding_manager()
    config = manager.load()
    return config.theme


@router.put("/theme", response_model=UITheme)
async def update_theme(theme: UITheme):
    """Update UI theme settings."""
    manager = get_branding_manager()
    current = manager.load()

    update_data = current.model_dump()
    update_data["theme"] = theme.model_dump()

    updated = BrandingConfig.model_validate(update_data)
    manager.save(updated)
    return updated.theme


@router.put("/theme/mode", response_model=UITheme)
async def set_theme_mode(request: ThemeModeRequest):
    """Set default theme mode (light, dark, or system)."""
    manager = get_branding_manager()
    current = manager.load()

    new_theme = UITheme(
        default_mode=request.mode,
        light=current.theme.light,
        dark=current.theme.dark,
        font_family=current.theme.font_family,
        font_family_mono=current.theme.font_family_mono,
        border_radius=current.theme.border_radius,
        border_radius_lg=current.theme.border_radius_lg,
    )

    update_data = current.model_dump()
    update_data["theme"] = new_theme.model_dump()

    updated = BrandingConfig.model_validate(update_data)
    manager.save(updated)
    return updated.theme


@router.get("/theme/colors/{mode}", response_model=ThemeColors)
async def get_theme_colors(mode: str):
    """Get color palette for specific theme mode."""
    manager = get_branding_manager()
    config = manager.load()

    try:
        theme_mode = ThemeMode(mode)
    except ValueError as err:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid theme mode: {mode}. Must be 'light', 'dark', or 'system'",
        ) from err

    return config.get_active_theme(theme_mode)


@router.get("/provider", response_model=Optional[ServiceProviderBranding])
async def get_provider_branding():
    """Get service provider branding."""
    manager = get_branding_manager()
    config = manager.load()
    return config.provider


@router.put("/provider", response_model=BrandingConfig)
async def update_provider_branding(provider: ServiceProviderBranding):
    """Update service provider branding."""
    manager = get_branding_manager()
    current = manager.load()

    update_data = current.model_dump()
    update_data["provider"] = provider.model_dump()

    updated = BrandingConfig.model_validate(update_data)
    manager.save(updated)
    return updated


@router.delete("/provider", response_model=BrandingConfig)
async def delete_provider_branding():
    """Remove service provider branding."""
    manager = get_branding_manager()
    current = manager.load()

    update_data = current.model_dump()
    update_data["provider"] = None

    updated = BrandingConfig.model_validate(update_data)
    manager.save(updated)
    return updated


@router.get("/client", response_model=Optional[ClientBranding])
async def get_client_branding():
    """Get client branding."""
    manager = get_branding_manager()
    config = manager.load()
    return config.client


@router.put("/client", response_model=BrandingConfig)
async def update_client_branding(client: ClientBranding):
    """Update client branding."""
    manager = get_branding_manager()
    current = manager.load()

    update_data = current.model_dump()
    update_data["client"] = client.model_dump()

    updated = BrandingConfig.model_validate(update_data)
    manager.save(updated)
    return updated


@router.delete("/client", response_model=BrandingConfig)
async def delete_client_branding():
    """Remove client branding."""
    manager = get_branding_manager()
    current = manager.load()

    update_data = current.model_dump()
    update_data["client"] = None

    updated = BrandingConfig.model_validate(update_data)
    manager.save(updated)
    return updated


def optimize_logo(image_data: bytes, max_height: int = 128) -> str:
    """Optimize logo image and return as base64 data URI."""
    img = Image.open(io.BytesIO(image_data))

    # Convert to RGB if necessary (e.g. for JPEG) or keep RGBA for PNG
    img = img.convert("RGBA") if img.mode in ("RGBA", "P") else img.convert("RGB")

    # Resize if height is too large
    if img.height > max_height:
        ratio = max_height / img.height
        new_width = int(img.width * ratio)
        img = img.resize((new_width, max_height), Image.Resampling.LANCZOS)

    # Save as PNG
    out_buf = io.BytesIO()
    img.save(out_buf, format="PNG", optimize=True)
    base64_data = base64.b64encode(out_buf.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{base64_data}"


@router.post("/logo/{logo_type}", response_model=BrandingConfig)
async def upload_logo(logo_type: str, file: UploadFile = File(...)):
    """Upload and optimize a logo image."""
    if logo_type not in ("provider", "provider_dark", "client", "client_dark"):
        raise HTTPException(status_code=400, detail="Invalid logo type")

    content = await file.read()
    try:
        base64_logo = optimize_logo(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}") from e

    manager = get_branding_manager()
    config = manager.load()

    if logo_type.startswith("provider"):
        if not config.provider:
            # Create default provider if doesn't exist
            config.provider = ServiceProviderBranding(name="My Organization")

        if logo_type == "provider":
            config.provider.logo_base64 = base64_logo
        else:
            config.provider.logo_dark_base64 = base64_logo
    else:
        if not config.client:
            config.client = ClientBranding(name="Default Client")

        if logo_type == "client":
            config.client.logo_base64 = base64_logo
        else:
            config.client.logo_dark_base64 = base64_logo

    manager.save(config)
    return config


@router.delete("/logo/{logo_type}", response_model=BrandingConfig)
async def delete_logo(logo_type: str):
    """Remove a logo image."""
    if logo_type not in ("provider", "provider_dark", "client", "client_dark"):
        raise HTTPException(status_code=400, detail="Invalid logo type")

    manager = get_branding_manager()
    config = manager.load()

    if logo_type.startswith("provider") and config.provider:
        if logo_type == "provider":
            config.provider.logo_base64 = None
        else:
            config.provider.logo_dark_base64 = None
    elif logo_type.startswith("client") and config.client:
        if logo_type == "client":
            config.client.logo_base64 = None
        else:
            config.client.logo_dark_base64 = None

    manager.save(config)
    return config

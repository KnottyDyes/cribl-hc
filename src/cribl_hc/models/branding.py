"""
Pydantic models for report branding, customization, and UI theming.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ThemeMode(str, Enum):
    """Available theme modes for the UI."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ThemeColors(BaseModel):
    """Color palette for a specific theme mode (light or dark)."""

    primary: str = Field(
        default="#00A3E0",
        description="Primary brand color.",
    )
    primary_hover: str = Field(
        default="#0082B3",
        description="Primary color hover state.",
    )
    primary_foreground: str = Field(
        default="#FFFFFF",
        description="Text color on primary background.",
    )
    secondary: str = Field(
        default="#0066A1",
        description="Secondary brand color.",
    )
    secondary_hover: str = Field(
        default="#005080",
        description="Secondary color hover state.",
    )
    secondary_foreground: str = Field(
        default="#FFFFFF",
        description="Text color on secondary background.",
    )
    accent: str = Field(
        default="#FFB81C",
        description="Accent color.",
    )
    accent_hover: str = Field(
        default="#E6A619",
        description="Accent color hover state.",
    )
    accent_foreground: str = Field(
        default="#1F2937",
        description="Text color on accent background.",
    )
    background: str = Field(
        default="#FFFFFF",
        description="Main page background color.",
    )
    background_secondary: str = Field(
        default="#F9FAFB",
        description="Secondary background.",
    )
    background_tertiary: str = Field(
        default="#F3F4F6",
        description="Tertiary background.",
    )
    foreground: str = Field(
        default="#111827",
        description="Primary text color.",
    )
    foreground_secondary: str = Field(
        default="#4B5563",
        description="Secondary text color.",
    )
    foreground_muted: str = Field(
        default="#9CA3AF",
        description="Muted text color.",
    )
    border: str = Field(
        default="#E5E7EB",
        description="Default border color.",
    )
    border_focus: str = Field(
        default="#00A3E0",
        description="Border color for focused elements.",
    )
    severity_critical: str = Field(
        default="#DC2626",
        description="Critical severity color.",
    )
    severity_high: str = Field(
        default="#EA580C",
        description="High severity color.",
    )
    severity_medium: str = Field(
        default="#F59E0B",
        description="Medium severity color.",
    )
    severity_low: str = Field(
        default="#3B82F6",
        description="Low severity color.",
    )
    severity_info: str = Field(
        default="#6B7280",
        description="Info severity color.",
    )
    success: str = Field(
        default="#10B981",
        description="Success status color.",
    )
    warning: str = Field(
        default="#F59E0B",
        description="Warning status color.",
    )
    error: str = Field(
        default="#EF4444",
        description="Error status color.",
    )

    @field_validator(
        "primary",
        "primary_hover",
        "primary_foreground",
        "secondary",
        "secondary_hover",
        "secondary_foreground",
        "accent",
        "accent_hover",
        "accent_foreground",
        "background",
        "background_secondary",
        "background_tertiary",
        "foreground",
        "foreground_secondary",
        "foreground_muted",
        "border",
        "border_focus",
        "severity_critical",
        "severity_high",
        "severity_medium",
        "severity_low",
        "severity_info",
        "success",
        "warning",
        "error",
        mode="before",
    )
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Validate that color is a valid CSS color format."""
        if not v:
            raise ValueError("Color cannot be empty")
        if v.startswith("#"):
            hex_part = v[1:]
            if len(hex_part) not in (3, 4, 6, 8):
                raise ValueError(f"Invalid hex color format: {v}")
            try:
                int(hex_part, 16)
            except ValueError:
                raise ValueError(f"Invalid hex color: {v}") from None
        return v

    model_config = {"populate_by_name": True}


# Dark theme default colors
DARK_THEME_DEFAULTS = ThemeColors(
    primary="#00A3E0",
    primary_hover="#33B5E7",
    primary_foreground="#FFFFFF",
    secondary="#0066A1",
    secondary_hover="#3385B5",
    secondary_foreground="#FFFFFF",
    accent="#FFB81C",
    accent_hover="#FFC94D",
    accent_foreground="#1F2937",
    background="#111827",
    background_secondary="#1F2937",
    background_tertiary="#374151",
    foreground="#F9FAFB",
    foreground_secondary="#D1D5DB",
    foreground_muted="#6B7280",
    border="#374151",
    border_focus="#00A3E0",
    severity_critical="#F87171",
    severity_high="#FB923C",
    severity_medium="#FBBF24",
    severity_low="#60A5FA",
    severity_info="#9CA3AF",
    success="#34D399",
    warning="#FBBF24",
    error="#F87171",
)


class UITheme(BaseModel):
    """UI theme configuration with light and dark mode palettes."""

    default_mode: ThemeMode = Field(
        default=ThemeMode.SYSTEM,
        description="Default theme mode.",
    )
    light: ThemeColors = Field(
        default_factory=lambda: ThemeColors(),
        description="Color palette for light mode.",
    )
    dark: ThemeColors = Field(
        default_factory=lambda: DARK_THEME_DEFAULTS.model_copy(),
        description="Color palette for dark mode.",
    )
    font_family: Optional[str] = Field(
        default=None,
        description="Custom font family.",
    )
    font_family_mono: Optional[str] = Field(
        default=None,
        description="Custom monospace font family.",
    )
    border_radius: str = Field(
        default="0.5rem",
        description="Default border radius.",
    )
    border_radius_lg: str = Field(
        default="0.75rem",
        description="Large border radius.",
    )

    model_config = {"populate_by_name": True}


class ServiceProviderBranding(BaseModel):
    """Branding for the company running the health check."""

    name: str = Field(..., description="Company name of the service provider.")
    logo_path: Optional[str] = None
    logo_path_dark: Optional[str] = None
    logo_url: Optional[HttpUrl] = None
    logo_url_dark: Optional[HttpUrl] = None
    logo_base64: Optional[str] = Field(default=None, description="Base64 encoded logo image.")
    logo_dark_base64: Optional[str] = Field(
        default=None, description="Base64 encoded dark mode logo."
    )
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[HttpUrl] = None
    footer_text: Optional[str] = None
    tagline: Optional[str] = None

    model_config = {"populate_by_name": True}


class ClientBranding(BaseModel):
    """Branding for the end customer receiving the report."""

    name: str = Field(..., description="Company name of the client.")
    logo_path: Optional[str] = Field(default=None, description="Path to the client's logo.")
    logo_path_dark: Optional[str] = Field(
        default=None, description="Alternative logo for dark mode."
    )
    logo_url: Optional[HttpUrl] = Field(default=None, description="URL to the client's logo.")
    logo_url_dark: Optional[HttpUrl] = Field(default=None, description="URL to the dark mode logo.")
    logo_base64: Optional[str] = Field(default=None, description="Base64 encoded logo image.")
    logo_dark_base64: Optional[str] = Field(
        default=None, description="Base64 encoded dark mode logo."
    )
    identifier: Optional[str] = Field(default=None, description="Client identifier.")
    report_title: Optional[str] = Field(default=None, description="Custom title for the report.")

    model_config = {"populate_by_name": True}


class ReportBranding(BaseModel):
    """Branding configuration specific to report generation."""

    show_provider_logo: bool = Field(default=True, description="Include service provider logo.")
    show_client_logo: bool = Field(default=True, description="Include client logo.")
    show_footer: bool = Field(default=True, description="Include branded footer.")
    show_watermark: bool = Field(default=False, description="Add watermark.")
    watermark_text: Optional[str] = Field(default=None, description="Custom watermark text.")
    custom_css: Optional[str] = Field(default=None, description="Custom CSS.")
    header_template: Optional[str] = Field(default=None, description="Custom header template.")
    footer_template: Optional[str] = Field(default=None, description="Custom footer template.")

    model_config = {"populate_by_name": True}


class BrandingConfig(BaseModel):
    """Container for all branding configurations."""

    provider: Optional[ServiceProviderBranding] = Field(
        default=None, description="Service provider branding details."
    )
    client: Optional[ClientBranding] = Field(
        default=None, description="Client-specific branding details."
    )
    theme: UITheme = Field(
        default_factory=lambda: UITheme(),
        description="UI theme configuration.",
    )
    report: ReportBranding = Field(
        default_factory=lambda: ReportBranding(),
        description="Report-specific branding options.",
    )

    @classmethod
    def default(cls) -> "BrandingConfig":
        """Create a default branding configuration."""
        return cls(
            provider=None,
            client=None,
        )

    def get_active_theme(self, mode: ThemeMode) -> ThemeColors:
        """Get the color palette for a specific theme mode."""
        if mode == ThemeMode.DARK:
            return self.theme.dark
        return self.theme.light

    model_config = {"populate_by_name": True}

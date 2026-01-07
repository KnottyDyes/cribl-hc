"""
Pydantic models for report branding, customization, and UI theming.

These models define the structure for service provider and client-specific
branding information that can be applied to generated health check reports
and the web UI (supporting dark/light mode themes).
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ThemeMode(str, Enum):
    """Available theme modes for the UI."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"  # Follow system preference


class ThemeColors(BaseModel):
    """Color palette for a specific theme mode (light or dark).

    All colors should be valid CSS color values (hex, rgb, hsl, etc.).
    Hex format recommended: '#RRGGBB' or '#RRGGBBAA'.
    """

    # Primary brand colors
    primary: str = Field(
        "#00A3E0",
        description="Primary brand color for buttons, links, and accents.",
    )
    primary_hover: str = Field(
        "#0082B3",
        description="Primary color hover state.",
    )
    primary_foreground: str = Field(
        "#FFFFFF",
        description="Text color on primary background.",
    )

    # Secondary brand colors
    secondary: str = Field(
        "#0066A1",
        description="Secondary brand color for less prominent elements.",
    )
    secondary_hover: str = Field(
        "#005080",
        description="Secondary color hover state.",
    )
    secondary_foreground: str = Field(
        "#FFFFFF",
        description="Text color on secondary background.",
    )

    # Accent color (for highlights, badges, etc.)
    accent: str = Field(
        "#FFB81C",
        description="Accent color for highlights and important elements.",
    )
    accent_hover: str = Field(
        "#E6A619",
        description="Accent color hover state.",
    )
    accent_foreground: str = Field(
        "#1F2937",
        description="Text color on accent background.",
    )

    # Background colors
    background: str = Field(
        "#FFFFFF",
        description="Main page background color.",
    )
    background_secondary: str = Field(
        "#F9FAFB",
        description="Secondary background (cards, panels).",
    )
    background_tertiary: str = Field(
        "#F3F4F6",
        description="Tertiary background (hover states, borders).",
    )

    # Foreground / text colors
    foreground: str = Field(
        "#111827",
        description="Primary text color.",
    )
    foreground_secondary: str = Field(
        "#4B5563",
        description="Secondary text color (subtitles, descriptions).",
    )
    foreground_muted: str = Field(
        "#9CA3AF",
        description="Muted text color (placeholders, disabled).",
    )

    # Border colors
    border: str = Field(
        "#E5E7EB",
        description="Default border color.",
    )
    border_focus: str = Field(
        "#00A3E0",
        description="Border color for focused elements.",
    )

    # Severity colors (for findings)
    severity_critical: str = Field(
        "#DC2626",
        description="Critical severity indicator.",
    )
    severity_high: str = Field(
        "#EA580C",
        description="High severity indicator.",
    )
    severity_medium: str = Field(
        "#F59E0B",
        description="Medium severity indicator.",
    )
    severity_low: str = Field(
        "#3B82F6",
        description="Low severity indicator.",
    )
    severity_info: str = Field(
        "#6B7280",
        description="Info severity indicator.",
    )

    # Status colors
    success: str = Field(
        "#10B981",
        description="Success status color.",
    )
    warning: str = Field(
        "#F59E0B",
        description="Warning status color.",
    )
    error: str = Field(
        "#EF4444",
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
        # Basic validation - hex colors should start with #
        if v.startswith("#"):
            # Validate hex format
            hex_part = v[1:]
            if len(hex_part) not in (3, 4, 6, 8):
                raise ValueError(f"Invalid hex color format: {v}")
            try:
                int(hex_part, 16)
            except ValueError:
                raise ValueError(f"Invalid hex color: {v}")
        # Allow other CSS color formats (rgb, hsl, named colors)
        return v


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
        ThemeMode.SYSTEM,
        description="Default theme mode (light, dark, or system).",
    )
    light: ThemeColors = Field(
        default_factory=lambda: ThemeColors(),
        description="Color palette for light mode.",
    )
    dark: ThemeColors = Field(
        default_factory=lambda: DARK_THEME_DEFAULTS.model_copy(),
        description="Color palette for dark mode.",
    )
    # Typography customization
    font_family: Optional[str] = Field(
        None,
        description="Custom font family CSS value. Uses system fonts if not specified.",
    )
    font_family_mono: Optional[str] = Field(
        None,
        description="Custom monospace font family for code blocks.",
    )
    # Border radius customization
    border_radius: str = Field(
        "0.5rem",
        description="Default border radius for UI elements.",
    )
    border_radius_lg: str = Field(
        "0.75rem",
        description="Large border radius for cards and panels.",
    )


class ServiceProviderBranding(BaseModel):
    """Branding for the company running the health check (e.g., MSP)."""

    name: str = Field(..., description="Company name of the service provider.")
    logo_path: Optional[str] = None
    logo_path_dark: Optional[str] = None
    logo_url: Optional[HttpUrl] = None
    logo_url_dark: Optional[HttpUrl] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[HttpUrl] = None
    footer_text: Optional[str] = None
    tagline: Optional[str] = None


class ClientBranding(BaseModel):
    """Branding for the end customer receiving the report."""

    name: str = Field(..., description="Company name of the client.")
    logo_path: Optional[str] = Field(None, description="Filesystem path to the client's logo.")
    logo_path_dark: Optional[str] = Field(
        None, description="Alternative logo for dark mode (if different)."
    )
    logo_url: Optional[HttpUrl] = Field(None, description="URL to the client's logo (remote).")
    logo_url_dark: Optional[HttpUrl] = Field(
        None, description="URL to the dark mode logo (remote)."
    )
    identifier: Optional[str] = Field(
        None, description="Client identifier (e.g., account number, department)."
    )
    report_title: Optional[str] = Field(None, description="Custom title for the report.")


class ReportBranding(BaseModel):
    """Branding configuration specific to report generation."""

    show_provider_logo: bool = Field(True, description="Include service provider logo in reports.")
    show_client_logo: bool = Field(True, description="Include client logo in reports.")
    show_footer: bool = Field(True, description="Include branded footer in reports.")
    show_watermark: bool = Field(False, description="Add watermark to report pages.")
    watermark_text: Optional[str] = Field(
        None, description="Custom watermark text (e.g., 'CONFIDENTIAL')."
    )
    custom_css: Optional[str] = Field(None, description="Custom CSS to inject into HTML reports.")
    header_template: Optional[str] = Field(
        None, description="Custom HTML template for report header."
    )
    footer_template: Optional[str] = Field(
        None, description="Custom HTML template for report footer."
    )


class BrandingConfig(BaseModel):
    """Container for all branding configurations.

    This is the main configuration object that encompasses:
    - Service provider branding (the company running health checks)
    - Client branding (the end customer receiving reports)
    - UI theme settings (dark/light mode, colors)
    - Report-specific branding options
    """

    provider: Optional[ServiceProviderBranding] = Field(
        None, description="Service provider branding details."
    )
    client: Optional[ClientBranding] = Field(None, description="Client-specific branding details.")
    theme: UITheme = Field(
        default_factory=lambda: UITheme(),
        description="UI theme configuration (dark/light mode, colors).",
    )
    report: ReportBranding = Field(
        default_factory=lambda: ReportBranding(),
        description="Report-specific branding options.",
    )

    @classmethod
    def default(cls) -> "BrandingConfig":
        """Create a default branding configuration with Cribl brand colors."""
        return cls(
            provider=None,
            client=None,
        )

    def get_active_theme(self, mode: ThemeMode) -> ThemeColors:
        """Get the color palette for a specific theme mode.

        Args:
            mode: The theme mode (light or dark). System mode defaults to light.

        Returns:
            The ThemeColors for the specified mode.
        """
        if mode == ThemeMode.DARK:
            return self.theme.dark
        return self.theme.light

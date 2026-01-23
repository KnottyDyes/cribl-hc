"""
True Zero Tech (TZT) Branding Constants

Extracted from TZT brand templates for consistent report styling.
"""

# Primary Colors
TZT_ORANGE = "#F26522"
TZT_ORANGE_DARK = "#EB4805"
TZT_DARK = "#231F20"
TZT_WHITE = "#FFFFFF"

# Grays
TZT_GRAY_DARK = "#58595B"
TZT_GRAY_MEDIUM = "#7D7E82"
TZT_GRAY_LIGHT = "#828282"

# Accent Colors
TZT_GREEN = "#6CAF3D"
TZT_PURPLE = "#7053AA"
TZT_RED = "#721923"
TZT_MAGENTA = "#A34499"

# Links
TZT_LINK = "#024B83"
TZT_LINK_VISITED = "#2895D5"

# Typography
TZT_FONT_PRIMARY = '"Times New Roman", Times, serif'
TZT_FONT_SANS = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'

# Severity Colors (mapped to TZT palette)
SEVERITY_COLORS = {
    "critical": TZT_RED,
    "high": TZT_ORANGE,
    "medium": "#F59E0B",  # Amber/yellow
    "low": TZT_LINK,
    "info": TZT_GRAY_MEDIUM,
}

# Status Colors
STATUS_COLORS = {
    "healthy": TZT_GREEN,
    "warning": TZT_ORANGE,
    "critical": TZT_RED,
    "compliant": TZT_GREEN,
    "at_risk": TZT_ORANGE,
    "non_compliant": TZT_RED,
}

# Logo as base64 (loaded from file)
import os
from pathlib import Path

def get_tzt_logo_base64() -> str:
    """Get the TZT logo as a base64 data URI."""
    assets_dir = Path(__file__).parent.parent / "assets"
    logo_b64_path = assets_dir / "tzt-logo-base64.txt"
    
    if logo_b64_path.exists():
        b64_data = logo_b64_path.read_text().strip()
        return f"data:image/png;base64,{b64_data}"
    return ""

TZT_LOGO_BASE64 = get_tzt_logo_base64()

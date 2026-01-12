"""Unit tests for branding models."""

import pytest
from pydantic import ValidationError

from cribl_hc.models.branding import (
    BrandingConfig,
    ClientBranding,
    ReportBranding,
    ServiceProviderBranding,
    ThemeColors,
    ThemeMode,
    UITheme,
)


class TestThemeColors:
    """Tests for ThemeColors model."""

    def test_default_colors(self):
        colors = ThemeColors()
        assert colors.primary == "#00A3E0"
        assert colors.background == "#FFFFFF"
        assert colors.foreground == "#111827"
        assert colors.severity_critical == "#DC2626"

    def test_custom_colors(self):
        colors = ThemeColors(
            primary="#FF5733",
            secondary="#33FF57",
            accent="#5733FF",
        )
        assert colors.primary == "#FF5733"
        assert colors.secondary == "#33FF57"
        assert colors.accent == "#5733FF"

    def test_valid_hex_formats(self):
        ThemeColors(primary="#FFF")
        ThemeColors(primary="#FFFF")
        ThemeColors(primary="#FFFFFF")
        ThemeColors(primary="#FFFFFFFF")

    def test_invalid_hex_format(self):
        with pytest.raises(ValidationError):
            ThemeColors(primary="#FFFFF")

    def test_invalid_hex_characters(self):
        with pytest.raises(ValidationError):
            ThemeColors(primary="#GGGGGG")

    def test_css_named_colors_allowed(self):
        colors = ThemeColors(primary="red", secondary="blue")
        assert colors.primary == "red"
        assert colors.secondary == "blue"

    def test_rgb_format_allowed(self):
        colors = ThemeColors(primary="rgb(255, 0, 0)")
        assert colors.primary == "rgb(255, 0, 0)"

    def test_empty_color_rejected(self):
        with pytest.raises(ValidationError):
            ThemeColors(primary="")


class TestUITheme:
    """Tests for UITheme model."""

    def test_default_theme(self):
        theme = UITheme()
        assert theme.default_mode == ThemeMode.SYSTEM
        assert theme.light.background == "#FFFFFF"
        assert theme.dark.background == "#111827"
        assert theme.border_radius == "0.5rem"

    def test_custom_light_dark_palettes(self):
        theme = UITheme(
            light=ThemeColors(primary="#1E88E5"),
            dark=ThemeColors(primary="#90CAF9"),
        )
        assert theme.light.primary == "#1E88E5"
        assert theme.dark.primary == "#90CAF9"

    def test_custom_font_family(self):
        theme = UITheme(
            font_family="'Roboto', sans-serif",
            font_family_mono="'Fira Code', monospace",
        )
        assert theme.font_family == "'Roboto', sans-serif"
        assert theme.font_family_mono == "'Fira Code', monospace"

    def test_border_radius_customization(self):
        theme = UITheme(
            border_radius="0.25rem",
            border_radius_lg="1rem",
        )
        assert theme.border_radius == "0.25rem"
        assert theme.border_radius_lg == "1rem"


class TestServiceProviderBranding:
    """Tests for ServiceProviderBranding model."""

    def test_minimal_provider(self):
        provider = ServiceProviderBranding(name="Acme Corp")
        assert provider.name == "Acme Corp"
        assert provider.logo_path is None
        assert provider.primary_color is None

    def test_full_provider(self):
        provider = ServiceProviderBranding(
            name="Acme Corp",
            logo_path="/path/to/logo.png",
            logo_path_dark="/path/to/logo-dark.png",
            logo_url="https://example.com/logo.png",
            primary_color="#1E88E5",
            secondary_color="#0D47A1",
            contact_email="support@acme.com",
            website="https://acme.com",
            footer_text="Copyright 2025 Acme Corp",
            tagline="We make things work",
        )
        assert provider.name == "Acme Corp"
        assert provider.logo_path == "/path/to/logo.png"
        assert provider.logo_path_dark == "/path/to/logo-dark.png"
        assert provider.primary_color == "#1E88E5"
        assert provider.tagline == "We make things work"


class TestClientBranding:
    """Tests for ClientBranding model."""

    def test_minimal_client(self):
        client = ClientBranding(name="Client Inc")
        assert client.name == "Client Inc"
        assert client.logo_path is None
        assert client.report_title is None

    def test_full_client(self):
        client = ClientBranding(
            name="Client Inc",
            logo_path="/path/to/client-logo.png",
            logo_path_dark="/path/to/client-logo-dark.png",
            identifier="CLT-001",
            report_title="Quarterly Health Assessment",
        )
        assert client.name == "Client Inc"
        assert client.identifier == "CLT-001"
        assert client.report_title == "Quarterly Health Assessment"


class TestReportBranding:
    """Tests for ReportBranding model."""

    def test_defaults(self):
        report = ReportBranding()
        assert report.show_provider_logo is True
        assert report.show_client_logo is True
        assert report.show_footer is True
        assert report.show_watermark is False
        assert report.watermark_text is None
        assert report.custom_css is None

    def test_custom_report_branding(self):
        report = ReportBranding(
            show_provider_logo=False,
            show_watermark=True,
            watermark_text="CONFIDENTIAL",
            custom_css="body { font-size: 14px; }",
            header_template="<h1>Custom Header</h1>",
            footer_template="<footer>Custom Footer</footer>",
        )
        assert report.show_provider_logo is False
        assert report.show_watermark is True
        assert report.watermark_text == "CONFIDENTIAL"
        assert "font-size" in (report.custom_css or "")


class TestBrandingConfig:
    """Tests for BrandingConfig model."""

    def test_default_config(self):
        config = BrandingConfig.default()
        assert config.provider is None
        assert config.client is None
        assert config.theme.default_mode == ThemeMode.SYSTEM
        assert config.report.show_provider_logo is True

    def test_full_config(self):
        config = BrandingConfig(
            provider=ServiceProviderBranding(name="MSP Corp"),
            client=ClientBranding(name="End Client"),
            theme=UITheme(default_mode=ThemeMode.DARK),
            report=ReportBranding(show_watermark=True),
        )
        assert config.provider is not None
        assert config.provider.name == "MSP Corp"
        assert config.client is not None
        assert config.client.name == "End Client"
        assert config.theme.default_mode == ThemeMode.DARK
        assert config.report.show_watermark is True

    def test_get_active_theme_light(self):
        config = BrandingConfig.default()
        colors = config.get_active_theme(ThemeMode.LIGHT)
        assert colors.background == "#FFFFFF"

    def test_get_active_theme_dark(self):
        config = BrandingConfig.default()
        colors = config.get_active_theme(ThemeMode.DARK)
        assert colors.background == "#111827"

    def test_get_active_theme_system_defaults_to_light(self):
        config = BrandingConfig.default()
        colors = config.get_active_theme(ThemeMode.SYSTEM)
        assert colors.background == "#FFFFFF"

    def test_serialization_roundtrip(self):
        config = BrandingConfig(
            provider=ServiceProviderBranding(
                name="Test Provider",
                primary_color="#FF0000",
            ),
            theme=UITheme(
                default_mode=ThemeMode.DARK,
                light=ThemeColors(primary="#AABBCC"),
            ),
        )

        json_str = config.model_dump_json()
        restored = BrandingConfig.model_validate_json(json_str)

        assert restored.provider is not None
        assert restored.provider.name == "Test Provider"
        assert restored.provider.primary_color == "#FF0000"
        assert restored.theme.default_mode == ThemeMode.DARK
        assert restored.theme.light.primary == "#AABBCC"


class TestThemeMode:
    """Tests for ThemeMode enum."""

    def test_values(self):
        assert ThemeMode.LIGHT.value == "light"
        assert ThemeMode.DARK.value == "dark"
        assert ThemeMode.SYSTEM.value == "system"

    def test_from_string(self):
        assert ThemeMode("light") == ThemeMode.LIGHT
        assert ThemeMode("dark") == ThemeMode.DARK
        assert ThemeMode("system") == ThemeMode.SYSTEM

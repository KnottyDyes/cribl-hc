"""Unit tests for branding manager."""

import tempfile
from pathlib import Path

import pytest

from cribl_hc.core.branding_manager import BrandingManager
from cribl_hc.models.branding import (
    BrandingConfig,
    ClientBranding,
    ServiceProviderBranding,
    ThemeMode,
    UITheme,
)


@pytest.fixture
def temp_config_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "branding.json"


@pytest.fixture
def manager(temp_config_path):
    return BrandingManager(config_path=temp_config_path)


class TestBrandingManager:
    def test_load_returns_defaults_when_no_file(self, manager, temp_config_path):
        assert not temp_config_path.exists()
        config = manager.load()
        assert config.provider is None
        assert config.client is None
        assert config.theme.default_mode == ThemeMode.SYSTEM

    def test_save_creates_file(self, manager, temp_config_path):
        config = BrandingConfig(provider=ServiceProviderBranding(name="Test Provider"))
        manager.save(config)
        assert temp_config_path.exists()

    def test_save_and_reload(self, manager):
        config = BrandingConfig(
            provider=ServiceProviderBranding(
                name="MSP Corp",
                primary_color="#FF0000",
            ),
            client=ClientBranding(
                name="Client Inc",
                identifier="CLT-001",
            ),
            theme=UITheme(default_mode=ThemeMode.DARK),
        )
        manager.save(config)

        reloaded = manager.reload()

        assert reloaded.provider is not None
        assert reloaded.provider.name == "MSP Corp"
        assert reloaded.provider.primary_color == "#FF0000"
        assert reloaded.client is not None
        assert reloaded.client.name == "Client Inc"
        assert reloaded.theme.default_mode == ThemeMode.DARK

    def test_load_caches_config(self, manager):
        first = manager.load()
        second = manager.load()
        assert first is second

    def test_reload_clears_cache(self, manager):
        first = manager.load()
        manager.reload()
        third = manager.load()
        assert first is not third

    def test_reset_returns_defaults(self, manager):
        custom = BrandingConfig(
            provider=ServiceProviderBranding(name="Custom"),
            theme=UITheme(default_mode=ThemeMode.DARK),
        )
        manager.save(custom)

        reset = manager.reset()

        assert reset.provider is None
        assert reset.theme.default_mode == ThemeMode.SYSTEM

    def test_delete_removes_file(self, manager, temp_config_path):
        manager.save(BrandingConfig.default())
        assert temp_config_path.exists()

        result = manager.delete()

        assert result is True
        assert not temp_config_path.exists()

    def test_delete_nonexistent_returns_false(self, manager, temp_config_path):
        assert not temp_config_path.exists()
        result = manager.delete()
        assert result is False

    def test_update_specific_fields(self, manager):
        initial = BrandingConfig(
            provider=ServiceProviderBranding(name="Original"),
        )
        manager.save(initial)

        new_provider = ServiceProviderBranding(name="Updated")
        updated = manager.update(provider=new_provider)

        assert updated.provider is not None
        assert updated.provider.name == "Updated"

    def test_config_path_property(self, manager, temp_config_path):
        assert manager.config_path == temp_config_path

    def test_load_handles_corrupt_file(self, manager, temp_config_path):
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text("{ invalid json", encoding="utf-8")

        config = manager.load()

        assert config.provider is None
        assert config.theme.default_mode == ThemeMode.SYSTEM

    def test_serialization_preserves_theme_colors(self, manager):
        from cribl_hc.models.branding import ThemeColors

        config = BrandingConfig(
            theme=UITheme(
                light=ThemeColors(
                    primary="#AABBCC",
                    background="#FFFFFF",
                ),
                dark=ThemeColors(
                    primary="#112233",
                    background="#000000",
                ),
            )
        )
        manager.save(config)
        reloaded = manager.reload()

        assert reloaded.theme.light.primary == "#AABBCC"
        assert reloaded.theme.dark.primary == "#112233"
        assert reloaded.theme.dark.background == "#000000"

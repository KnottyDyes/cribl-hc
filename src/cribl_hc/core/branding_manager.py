"""Branding configuration storage and management."""

import json
from pathlib import Path
from typing import Optional

from cribl_hc.models.branding import BrandingConfig
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)

CONFIG_DIR = Path.home() / ".cribl-hc"
BRANDING_FILE = CONFIG_DIR / "branding.json"


class BrandingManager:
    """Manages branding configuration storage and retrieval."""

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path or BRANDING_FILE
        self._config: Optional[BrandingConfig] = None

    @property
    def config_path(self) -> Path:
        return self._config_path

    def _ensure_config_dir(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.parent.chmod(0o700)

    def load(self) -> BrandingConfig:
        """Load branding configuration from disk."""
        if self._config is not None:
            return self._config

        if not self._config_path.exists():
            log.info("branding_config_not_found", path=str(self._config_path))
            self._config = BrandingConfig.default()
            return self._config

        try:
            json_data = self._config_path.read_text(encoding="utf-8")
            self._config = BrandingConfig.model_validate_json(json_data)
            log.info("branding_config_loaded", path=str(self._config_path))
            return self._config
        except Exception as e:
            log.error("branding_config_load_error", error=str(e), path=str(self._config_path))
            self._config = BrandingConfig.default()
            return self._config

    def save(self, config: BrandingConfig) -> None:
        """Save branding configuration to disk."""
        self._ensure_config_dir()
        json_data = config.model_dump_json(indent=2)
        self._config_path.write_text(json_data, encoding="utf-8")
        self._config_path.chmod(0o644)
        self._config = config
        log.info("branding_config_saved", path=str(self._config_path))

    def update(self, **kwargs) -> BrandingConfig:
        """Update specific fields in the branding configuration."""
        current = self.load()
        updated_data = current.model_dump()

        for key, value in kwargs.items():
            if key in updated_data and value is not None:
                updated_data[key] = value

        updated_config = BrandingConfig.model_validate(updated_data)
        self.save(updated_config)
        return updated_config

    def reset(self) -> BrandingConfig:
        """Reset branding to defaults."""
        default_config = BrandingConfig.default()
        self.save(default_config)
        log.info("branding_config_reset")
        return default_config

    def delete(self) -> bool:
        """Delete branding configuration file."""
        if self._config_path.exists():
            self._config_path.unlink()
            self._config = None
            log.info("branding_config_deleted", path=str(self._config_path))
            return True
        return False

    def reload(self) -> BrandingConfig:
        """Force reload from disk, discarding cached config."""
        self._config = None
        return self.load()


_default_manager: Optional[BrandingManager] = None


def get_branding_manager() -> BrandingManager:
    """Get the default branding manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = BrandingManager()
    return _default_manager


def get_branding_config() -> BrandingConfig:
    """Convenience function to get current branding configuration."""
    return get_branding_manager().load()

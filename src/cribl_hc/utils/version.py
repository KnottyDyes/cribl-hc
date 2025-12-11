"""
Cribl version detection and compatibility checking.

Supports Cribl Stream versions N (current), N-1, and N-2.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from cribl_hc.utils.logger import get_logger


log = get_logger(__name__)


class CriblVersion(BaseModel):
    """
    Parsed Cribl Stream version.

    Attributes:
        major: Major version number
        minor: Minor version number
        patch: Patch version number
        build: Build number (optional)
        raw: Raw version string
    """

    major: int = Field(..., description="Major version", ge=0)
    minor: int = Field(..., description="Minor version", ge=0)
    patch: int = Field(..., description="Patch version", ge=0)
    build: Optional[str] = Field(None, description="Build number")
    raw: str = Field(..., description="Raw version string")

    @field_validator("raw")
    @classmethod
    def validate_raw_format(cls, v: str) -> str:
        """Validate raw version string format."""
        if not re.match(r'^\d+\.\d+\.\d+', v):
            raise ValueError("Version must be in format X.Y.Z or X.Y.Z-build")
        return v

    def __str__(self) -> str:
        """String representation of version."""
        if self.build:
            return f"{self.major}.{self.minor}.{self.patch}-{self.build}"
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "CriblVersion") -> bool:
        """Less than comparison."""
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "CriblVersion") -> bool:
        """Less than or equal comparison."""
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __gt__(self, other: "CriblVersion") -> bool:
        """Greater than comparison."""
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other: "CriblVersion") -> bool:
        """Greater than or equal comparison."""
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, CriblVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def to_tuple(self) -> tuple[int, int, int]:
        """Convert to tuple for easy comparison."""
        return (self.major, self.minor, self.patch)


def parse_version(version_string: str) -> CriblVersion:
    """
    Parse a Cribl version string into structured format.

    Supports formats:
    - X.Y.Z (e.g., "4.5.2")
    - X.Y.Z-build (e.g., "4.5.2-ab12cd34")

    Args:
        version_string: Version string to parse

    Returns:
        Parsed CriblVersion object

    Raises:
        ValueError: If version string is invalid

    Example:
        >>> version = parse_version("4.5.2")
        >>> print(version.major, version.minor, version.patch)
        4 5 2
        >>> version = parse_version("4.5.2-ab12cd34")
        >>> print(version.build)
        ab12cd34
    """
    # Match version pattern: X.Y.Z or X.Y.Z-build
    pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$'
    match = re.match(pattern, version_string.strip())

    if not match:
        raise ValueError(
            f"Invalid version format: '{version_string}'. "
            "Expected format: X.Y.Z or X.Y.Z-build"
        )

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    build = match.group(4)  # Optional build number

    return CriblVersion(
        major=major,
        minor=minor,
        patch=patch,
        build=build,
        raw=version_string.strip(),
    )


def detect_version(version_data: dict) -> Optional[CriblVersion]:
    """
    Detect Cribl version from API response data.

    Args:
        version_data: Response from /api/v1/version endpoint

    Returns:
        Parsed CriblVersion or None if detection failed

    Example:
        >>> version_data = {"version": "4.5.2", "build": "12345"}
        >>> version = detect_version(version_data)
        >>> print(version)
        4.5.2
    """
    try:
        # Try to get version string from various possible keys
        version_string = None

        if isinstance(version_data, dict):
            # Common keys: version, productVersion, versionNumber
            for key in ["version", "productVersion", "versionNumber", "ver"]:
                if key in version_data:
                    version_string = str(version_data[key])
                    break

        if not version_string:
            log.warning("version_detection_failed", data=version_data)
            return None

        version = parse_version(version_string)
        log.info("version_detected", version=str(version))
        return version

    except Exception as e:
        log.error("version_parse_error", error=str(e), data=version_data)
        return None


def is_version_supported(version: CriblVersion, current_version: Optional[CriblVersion] = None) -> bool:
    """
    Check if a Cribl version is supported (N, N-1, or N-2).

    Args:
        version: Version to check
        current_version: Current/latest Cribl version (default: 4.7.0 as of 2025)

    Returns:
        True if version is supported (N through N-2), False otherwise

    Example:
        >>> current = parse_version("4.7.0")
        >>> is_version_supported(parse_version("4.7.0"), current)  # N
        True
        >>> is_version_supported(parse_version("4.6.0"), current)  # N-1
        True
        >>> is_version_supported(parse_version("4.5.0"), current)  # N-2
        True
        >>> is_version_supported(parse_version("4.4.0"), current)  # N-3
        False
    """
    if current_version is None:
        # Default to a recent version if not specified
        # This should be updated periodically or fetched dynamically
        current_version = parse_version("4.7.0")

    # Calculate N-2 version (two minor versions back)
    # Cribl typically maintains compatibility for 2 minor versions
    min_supported_minor = max(0, current_version.minor - 2)

    # Check if version is within supported range
    if version.major != current_version.major:
        # Different major version - not supported
        log.warning(
            "version_not_supported_major",
            version=str(version),
            current=str(current_version),
        )
        return False

    if version.minor < min_supported_minor:
        # Too old (before N-2)
        log.warning(
            "version_not_supported_old",
            version=str(version),
            current=str(current_version),
            minimum=f"{current_version.major}.{min_supported_minor}.0",
        )
        return False

    if version.minor > current_version.minor:
        # Newer than current (might work, but log warning)
        log.info(
            "version_newer_than_current",
            version=str(version),
            current=str(current_version),
        )
        return True

    # Version is N, N-1, or N-2
    log.info("version_supported", version=str(version), current=str(current_version))
    return True


def get_version_compatibility_message(version: CriblVersion, current_version: Optional[CriblVersion] = None) -> str:
    """
    Get a human-readable compatibility message for a version.

    Args:
        version: Version to check
        current_version: Current/latest version

    Returns:
        Compatibility message

    Example:
        >>> v = parse_version("4.5.0")
        >>> print(get_version_compatibility_message(v, parse_version("4.7.0")))
        'Version 4.5.0 is supported (N-2)'
    """
    if current_version is None:
        current_version = parse_version("4.7.0")

    if not is_version_supported(version, current_version):
        return (
            f"Version {version} is NOT supported. "
            f"Supported versions: {current_version.major}.{max(0, current_version.minor - 2)}.x "
            f"through {current_version.major}.{current_version.minor}.x"
        )

    # Calculate version designation (N, N-1, N-2)
    version_diff = current_version.minor - version.minor

    if version_diff == 0:
        designation = "current (N)"
    elif version_diff == 1:
        designation = "N-1"
    elif version_diff == 2:
        designation = "N-2"
    elif version.minor > current_version.minor:
        designation = "newer than current"
    else:
        designation = "unknown"

    return f"Version {version} is supported ({designation})"


# Version constants for common checks
MINIMUM_SUPPORTED_MAJOR_VERSION = 4
MINIMUM_SUPPORTED_MINOR_VERSION = 5  # 4.5.x and up

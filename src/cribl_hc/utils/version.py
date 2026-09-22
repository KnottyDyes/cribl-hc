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
    Check if a Cribl version is supported.

    Support policy: every 4.x release at or above the
    ``MINIMUM_SUPPORTED_MAJOR_VERSION.MINIMUM_SUPPORTED_MINOR_VERSION`` floor
    (4.5) is supported. Releases below the floor, and other major versions,
    are not.

    Args:
        version: Version to check
        current_version: Latest known Cribl version, used only to note when a
            deployment is newer than this tool has been validated against
            (default: ``LATEST_KNOWN_VERSION``)

    Returns:
        True if the version is within the supported 4.x range, False otherwise

    Example:
        >>> is_version_supported(parse_version("4.20.0"))
        True
        >>> is_version_supported(parse_version("4.5.0"))
        True
        >>> is_version_supported(parse_version("4.4.0"))  # below the 4.5 floor
        False
        >>> is_version_supported(parse_version("3.9.0"))  # unsupported major
        False
    """
    if current_version is None:
        current_version = parse_version(LATEST_KNOWN_VERSION)

    if version.major != MINIMUM_SUPPORTED_MAJOR_VERSION:
        log.warning(
            "version_not_supported_major",
            version=str(version),
            supported_major=MINIMUM_SUPPORTED_MAJOR_VERSION,
        )
        return False

    if version.minor < MINIMUM_SUPPORTED_MINOR_VERSION:
        log.warning(
            "version_not_supported_old",
            version=str(version),
            minimum=f"{MINIMUM_SUPPORTED_MAJOR_VERSION}.{MINIMUM_SUPPORTED_MINOR_VERSION}.0",
        )
        return False

    if version > current_version:
        # Within the supported major line but newer than this tool has been
        # validated against; analysis proceeds, results may miss new features.
        log.info(
            "version_newer_than_validated",
            version=str(version),
            latest_known=str(current_version),
        )
        return True

    log.info("version_supported", version=str(version))
    return True


def get_version_compatibility_message(version: CriblVersion, current_version: Optional[CriblVersion] = None) -> str:
    """
    Get a human-readable compatibility message for a version.

    Args:
        version: Version to check
        current_version: Latest known Cribl version

    Returns:
        Compatibility message

    Example:
        >>> print(get_version_compatibility_message(parse_version("4.5.0")))
        'Version 4.5.0 is supported (N-15)'
    """
    if current_version is None:
        current_version = parse_version(LATEST_KNOWN_VERSION)

    minimum = f"{MINIMUM_SUPPORTED_MAJOR_VERSION}.{MINIMUM_SUPPORTED_MINOR_VERSION}"
    if not is_version_supported(version, current_version):
        return (
            f"Version {version} is NOT supported. "
            f"Supported versions: {minimum}.x "
            f"through {current_version.major}.{current_version.minor}.x"
        )

    if version > current_version:
        return (
            f"Version {version} is supported (newer than {current_version}, "
            f"the latest release this tool has been validated against)"
        )

    version_diff = current_version.minor - version.minor
    if version_diff == 0:
        designation = "current (N)"
    else:
        designation = f"N-{version_diff}"

    return f"Version {version} is supported ({designation})"


# Version constants for common checks
MINIMUM_SUPPORTED_MAJOR_VERSION = 4
MINIMUM_SUPPORTED_MINOR_VERSION = 5  # 4.5.x and up

# Latest Cribl release this tool has been validated against. Deployments newer
# than this still analyze; update alongside cribl_api_reference/.
LATEST_KNOWN_VERSION = "4.20.0"

"""
Unit tests for Cribl version detection and compatibility checking.
"""

import pytest
from pydantic import ValidationError

from cribl_hc.utils.version import (
    CriblVersion,
    parse_version,
    detect_version,
    is_version_supported,
    get_version_compatibility_message,
)


class TestCriblVersion:
    """Test CriblVersion model."""

    def test_valid_version_creation(self):
        """Test creating a valid version."""
        version = CriblVersion(
            major=4,
            minor=5,
            patch=2,
            build="ab12cd34",
            raw="4.5.2-ab12cd34",
        )

        assert version.major == 4
        assert version.minor == 5
        assert version.patch == 2
        assert version.build == "ab12cd34"
        assert version.raw == "4.5.2-ab12cd34"

    def test_version_without_build(self):
        """Test version without build number."""
        version = CriblVersion(
            major=4,
            minor=5,
            patch=2,
            raw="4.5.2",
        )

        assert version.major == 4
        assert version.minor == 5
        assert version.patch == 2
        assert version.build is None

    def test_version_string_representation(self):
        """Test string representation of version."""
        version = CriblVersion(major=4, minor=5, patch=2, raw="4.5.2")
        assert str(version) == "4.5.2"

        version_with_build = CriblVersion(
            major=4, minor=5, patch=2, build="abc123", raw="4.5.2-abc123"
        )
        assert str(version_with_build) == "4.5.2-abc123"

    def test_invalid_raw_format(self):
        """Test that invalid raw format is rejected."""
        with pytest.raises(ValidationError):
            CriblVersion(major=4, minor=5, patch=2, raw="invalid")

        with pytest.raises(ValidationError):
            CriblVersion(major=4, minor=5, patch=2, raw="4.5")

    def test_version_comparison_less_than(self):
        """Test version less than comparison."""
        v1 = CriblVersion(major=4, minor=5, patch=0, raw="4.5.0")
        v2 = CriblVersion(major=4, minor=5, patch=1, raw="4.5.1")
        v3 = CriblVersion(major=4, minor=6, patch=0, raw="4.6.0")
        v4 = CriblVersion(major=5, minor=0, patch=0, raw="5.0.0")

        assert v1 < v2
        assert v1 < v3
        assert v1 < v4
        assert v2 < v3
        assert v3 < v4

    def test_version_comparison_greater_than(self):
        """Test version greater than comparison."""
        v1 = CriblVersion(major=4, minor=5, patch=2, raw="4.5.2")
        v2 = CriblVersion(major=4, minor=5, patch=1, raw="4.5.1")
        v3 = CriblVersion(major=4, minor=4, patch=9, raw="4.4.9")

        assert v1 > v2
        assert v1 > v3
        assert v2 > v3

    def test_version_comparison_equal(self):
        """Test version equality comparison."""
        v1 = CriblVersion(major=4, minor=5, patch=2, raw="4.5.2")
        v2 = CriblVersion(major=4, minor=5, patch=2, raw="4.5.2")
        v3 = CriblVersion(major=4, minor=5, patch=2, build="abc", raw="4.5.2-abc")

        assert v1 == v2
        assert v1 == v3  # Build doesn't affect equality

    def test_version_to_tuple(self):
        """Test converting version to tuple."""
        version = CriblVersion(major=4, minor=5, patch=2, raw="4.5.2")
        assert version.to_tuple() == (4, 5, 2)


class TestParseVersion:
    """Test version parsing."""

    def test_parse_simple_version(self):
        """Test parsing simple X.Y.Z version."""
        version = parse_version("4.5.2")

        assert version.major == 4
        assert version.minor == 5
        assert version.patch == 2
        assert version.build is None
        assert version.raw == "4.5.2"

    def test_parse_version_with_build(self):
        """Test parsing version with build number."""
        version = parse_version("4.5.2-ab12cd34")

        assert version.major == 4
        assert version.minor == 5
        assert version.patch == 2
        assert version.build == "ab12cd34"
        assert version.raw == "4.5.2-ab12cd34"

    def test_parse_version_with_whitespace(self):
        """Test parsing version with surrounding whitespace."""
        version = parse_version("  4.5.2  ")

        assert version.major == 4
        assert version.minor == 5
        assert version.patch == 2

    def test_parse_various_versions(self):
        """Test parsing various version formats."""
        test_cases = [
            ("4.0.0", 4, 0, 0, None),
            ("4.7.3", 4, 7, 3, None),
            ("5.0.0-beta", 5, 0, 0, "beta"),
            ("4.5.2-12345678", 4, 5, 2, "12345678"),
        ]

        for version_str, expected_major, expected_minor, expected_patch, expected_build in test_cases:
            version = parse_version(version_str)
            assert version.major == expected_major
            assert version.minor == expected_minor
            assert version.patch == expected_patch
            assert version.build == expected_build

    def test_parse_invalid_versions(self):
        """Test that invalid versions raise errors."""
        invalid_versions = [
            "4.5",  # Missing patch
            "4",  # Only major
            "invalid",  # Not a version
            "4.5.x",  # Non-numeric
            "v4.5.2",  # Has prefix
            "",  # Empty
        ]

        for invalid in invalid_versions:
            with pytest.raises(ValueError):
                parse_version(invalid)


class TestDetectVersion:
    """Test version detection from API responses."""

    def test_detect_version_from_standard_response(self):
        """Test detecting version from standard API response."""
        response_data = {
            "version": "4.5.2",
            "build": "12345",
            "product": "Stream",
        }

        version = detect_version(response_data)

        assert version is not None
        assert version.major == 4
        assert version.minor == 5
        assert version.patch == 2

    def test_detect_version_alternative_keys(self):
        """Test detecting version from various response formats."""
        test_cases = [
            {"version": "4.5.2"},
            {"productVersion": "4.6.0"},
            {"versionNumber": "4.7.1"},
            {"ver": "4.8.0"},
        ]

        for response_data in test_cases:
            version = detect_version(response_data)
            assert version is not None
            assert version.major == 4

    def test_detect_version_missing_key(self):
        """Test detection returns None when version key missing."""
        response_data = {
            "build": "12345",
            "product": "Stream",
        }

        version = detect_version(response_data)
        assert version is None

    def test_detect_version_invalid_format(self):
        """Test detection handles invalid version formats."""
        response_data = {"version": "invalid-version"}

        version = detect_version(response_data)
        assert version is None

    def test_detect_version_non_dict_input(self):
        """Test detection handles non-dict input."""
        version = detect_version("not-a-dict")
        assert version is None

        version = detect_version(None)
        assert version is None


class TestVersionSupport:
    """Test version support checking."""

    def test_current_version_supported(self):
        """Test that current version (N) is supported."""
        current = parse_version("4.7.0")
        version = parse_version("4.7.0")

        assert is_version_supported(version, current) is True

    def test_n_minus_1_supported(self):
        """Test that N-1 version is supported."""
        current = parse_version("4.7.0")
        version = parse_version("4.6.5")

        assert is_version_supported(version, current) is True

    def test_n_minus_2_supported(self):
        """Test that N-2 version is supported."""
        current = parse_version("4.7.0")
        version = parse_version("4.5.3")

        assert is_version_supported(version, current) is True

    def test_n_minus_3_not_supported(self):
        """Test that N-3 version is not supported."""
        current = parse_version("4.7.0")
        version = parse_version("4.4.0")

        assert is_version_supported(version, current) is False

    def test_different_major_not_supported(self):
        """Test that different major version is not supported."""
        current = parse_version("4.7.0")
        version = parse_version("3.9.0")

        assert is_version_supported(version, current) is False

        version = parse_version("5.0.0")
        assert is_version_supported(version, current) is False

    def test_newer_version_supported(self):
        """Test that newer minor version is supported."""
        current = parse_version("4.5.0")
        version = parse_version("4.6.0")

        # Newer versions should be supported (might work)
        assert is_version_supported(version, current) is True

    def test_support_with_default_current(self):
        """Test version support without specifying current version."""
        # Should use default current version
        version = parse_version("4.5.0")
        result = is_version_supported(version)

        # Result depends on default version, just check it returns bool
        assert isinstance(result, bool)


class TestVersionCompatibilityMessage:
    """Test compatibility message generation."""

    def test_compatibility_message_current(self):
        """Test message for current version."""
        current = parse_version("4.7.0")
        version = parse_version("4.7.0")

        message = get_version_compatibility_message(version, current)

        assert "supported" in message.lower()
        assert "current (N)" in message or "4.7.0" in message

    def test_compatibility_message_n_minus_1(self):
        """Test message for N-1 version."""
        current = parse_version("4.7.0")
        version = parse_version("4.6.0")

        message = get_version_compatibility_message(version, current)

        assert "supported" in message.lower()
        assert "N-1" in message or "4.6.0" in message

    def test_compatibility_message_n_minus_2(self):
        """Test message for N-2 version."""
        current = parse_version("4.7.0")
        version = parse_version("4.5.0")

        message = get_version_compatibility_message(version, current)

        assert "supported" in message.lower()
        assert "N-2" in message or "4.5.0" in message

    def test_compatibility_message_not_supported(self):
        """Test message for unsupported version."""
        current = parse_version("4.7.0")
        version = parse_version("4.3.0")

        message = get_version_compatibility_message(version, current)

        assert "not supported" in message.lower()
        assert "4.5" in message  # Should show minimum supported

    def test_compatibility_message_newer(self):
        """Test message for newer version."""
        current = parse_version("4.5.0")
        version = parse_version("4.7.0")

        message = get_version_compatibility_message(version, current)

        assert "supported" in message.lower()
        assert "newer" in message.lower() or "4.7.0" in message


class TestVersionEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_version_zero_components(self):
        """Test version with zero components."""
        version = parse_version("0.0.0")
        assert version.major == 0
        assert version.minor == 0
        assert version.patch == 0

    def test_version_large_numbers(self):
        """Test version with large version numbers."""
        version = parse_version("99.99.99")
        assert version.major == 99
        assert version.minor == 99
        assert version.patch == 99

    def test_version_comparison_with_different_types(self):
        """Test version comparison with non-version objects."""
        version = CriblVersion(major=4, minor=5, patch=2, raw="4.5.2")

        # Comparing with non-version should return NotImplemented
        result = version.__eq__("4.5.2")
        assert result == NotImplemented

    def test_build_number_variations(self):
        """Test various build number formats."""
        build_formats = [
            "4.5.2-abc123",
            "4.5.2-123",
            "4.5.2-beta-1",
            "4.5.2-SNAPSHOT",
        ]

        for version_str in build_formats:
            version = parse_version(version_str)
            assert version is not None
            assert version.build is not None

    def test_version_less_than_or_equal(self):
        """Test version <= comparison."""
        v1 = CriblVersion(major=4, minor=5, patch=0, raw="4.5.0")
        v2 = CriblVersion(major=4, minor=5, patch=0, raw="4.5.0")
        v3 = CriblVersion(major=4, minor=5, patch=1, raw="4.5.1")

        assert v1 <= v2
        assert v1 <= v3
        assert not (v3 <= v1)

    def test_version_greater_than_or_equal(self):
        """Test version >= comparison."""
        v1 = CriblVersion(major=4, minor=5, patch=2, raw="4.5.2")
        v2 = CriblVersion(major=4, minor=5, patch=2, raw="4.5.2")
        v3 = CriblVersion(major=4, minor=5, patch=1, raw="4.5.1")

        assert v1 >= v2
        assert v1 >= v3
        assert not (v3 >= v1)

    def test_detect_version_with_nested_data(self):
        """Test detection with nested version data."""
        response_data = {
            "data": {
                "version": "4.8.0"
            },
            "build": "12345"
        }

        # Should look at top-level first
        version = detect_version(response_data)
        # If it doesn't find it at top level, it will return None
        # This tests the lookup order

    def test_version_compatibility_edge_cases(self):
        """Test version compatibility with edge cases."""
        current = parse_version("4.7.0")

        # Test exact boundary at N-2
        version_n2 = parse_version("4.5.0")
        assert is_version_supported(version_n2, current) is True

        # Test just below N-2 (should not be supported)
        version_n3 = parse_version("4.4.9")
        assert is_version_supported(version_n3, current) is False

    def test_compatibility_message_major_mismatch(self):
        """Test compatibility message for different major versions."""
        current = parse_version("5.0.0")
        old_major = parse_version("4.9.0")

        message = get_version_compatibility_message(old_major, current)
        assert "not supported" in message.lower()

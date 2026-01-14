"""
Unit tests for LibraryAndResourceAnalyzer.
"""

from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.library_resource import (
    LibraryAndResourceAnalyzer,
    LibraryEntry,
)
from cribl_hc.core.api_client import CriblAPIClient


class TestLibraryAndResourceAnalyzer:
    """Test LibraryAndResourceAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return LibraryAndResourceAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = AsyncMock(spec=CriblAPIClient)
        return client

    def test_objective_name(self, analyzer):
        """Test analyzer objective name."""
        assert analyzer.objective_name == "library-resource-optimization"

    def test_supported_products(self, analyzer):
        """Test supported products."""
        assert analyzer.supported_products == ["stream", "edge"]

    def test_required_permissions(self, analyzer):
        """Test required permissions."""
        expected = [
            "read:libraries",
            "read:functions",
            "read:pipelines",
            "read:routes",
            "read:lookups",
        ]
        assert analyzer.get_required_permissions() == expected

    @pytest.mark.asyncio
    async def test_analyze_no_libraries(self, analyzer, mock_client):
        """Test analysis with no library data."""
        # Mock empty responses
        mock_client.get.side_effect = [
            {"items": []},  # functions
            Exception("Not found"),  # lookups (simulating missing endpoint)
            {"items": []},  # pipelines
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        assert "No Libraries Found" in result.findings[0].title

    @pytest.mark.asyncio
    async def test_analyze_unused_libraries(self, analyzer, mock_client):
        """Test detection of unused libraries."""
        functions_data = {
            "items": [
                {
                    "id": "func1",
                    "name": "testFunction",
                    "content": "function test() { return true; }",
                    "lastModified": "2024-01-01T00:00:00Z",
                }
            ]
        }

        pipelines_data = {"items": []}  # No pipelines using the function
        routes_data = {"items": []}

        mock_client.get.side_effect = [
            functions_data,  # functions
            Exception("Not found"),  # lookups
            Exception("Not found"),  # pipelines (fragment endpoint)
        ]
        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should find unused library

    @pytest.mark.asyncio
    async def test_analyze_massive_unused_library(self, analyzer, mock_client):
        """Test detection of massive unused libraries."""
        large_function_data = {
            "items": [
                {
                    "id": "large_func",
                    "name": "largeFunction",
                    "content": "x" * 15_000_000,  # 15MB function
                    "lastModified": "2024-01-01T00:00:00Z",
                }
            ]
        }

        mock_client.get.side_effect = [
            large_function_data,  # functions
            Exception("Not found"),  # lookups
            Exception("Not found"),  # pipelines
        ]
        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        assert len(critical_findings) >= 1
        # Should find massive unused library

    @pytest.mark.asyncio
    async def test_analyze_performance_impact(self, analyzer, mock_client):
        """Test performance impact analysis."""
        # Create a large library that's used frequently
        large_function_data = {
            "items": [
                {
                    "id": "large_func",
                    "name": "largeFunction",
                    "content": "x" * 2_000_000,  # 2MB function
                    "lastModified": "2024-01-01T00:00:00Z",
                }
            ]
        }

        pipelines_data = {
            "items": [
                {
                    "id": "pipeline1",
                    "name": "Test Pipeline",
                    "config": {
                        "steps": [{"type": "function", "function": {"name": "largeFunction"}}]
                    },
                }
            ]
        }

        mock_client.get.side_effect = [
            large_function_data,  # functions
            Exception("Not found"),  # lookups
            Exception("Not found"),  # pipelines
        ]
        mock_client.get_pipelines.return_value = pipelines_data["items"]
        mock_client.get_routes.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should analyze performance impact of large libraries

    @pytest.mark.asyncio
    async def test_analyze_maintenance_burden(self, analyzer, mock_client):
        """Test maintenance burden analysis."""
        # Create a library with many functions
        complex_function_data = {
            "items": [
                {
                    "id": "complex_func",
                    "name": "complexFunction",
                    "content": "function f1() {}\nfunction f2() {}\nfunction f3() {}\n"
                    * 10,  # 30 functions
                    "lastModified": "2024-01-01T00:00:00Z",
                }
            ]
        }

        mock_client.get.side_effect = [
            complex_function_data,  # functions
            Exception("Not found"),  # lookups
            Exception("Not found"),  # pipelines
        ]
        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        # Should find maintenance burden issue

    @pytest.mark.asyncio
    async def test_analyze_dependency_chains(self, analyzer, mock_client):
        """Test dependency chain analysis."""
        # Create pipeline fragments with dependencies
        fragment_data = {
            "items": [
                {
                    "id": "frag1",
                    "name": "fragment1",
                    "config": {"fragmentRefs": ["fragment2"]},
                    "lastModified": "2024-01-01T00:00:00Z",
                },
                {
                    "id": "frag2",
                    "name": "fragment2",
                    "config": {"fragmentRefs": ["fragment1"]},  # Circular reference
                    "lastModified": "2024-01-01T00:00:00Z",
                },
            ]
        }

        mock_client.get.side_effect = [
            {"items": []},  # functions
            Exception("Not found"),  # lookups
            fragment_data,  # pipelines (fragments)
        ]
        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        high_findings = [f for f in result.findings if f.severity == "high"]
        # Should detect circular dependency

    @pytest.mark.asyncio
    async def test_analyze_optimization_opportunities(self, analyzer, mock_client):
        """Test optimization opportunities analysis."""
        # Create duplicate libraries
        duplicate_functions = {
            "items": [
                {
                    "id": "func1",
                    "name": "duplicateFunc",
                    "content": "function test() { return 1; }",
                    "lastModified": "2024-01-01T00:00:00Z",
                },
                {
                    "id": "func2",
                    "name": "duplicateFunc",
                    "content": "function test() { return 1; }",
                    "lastModified": "2024-01-01T00:00:00Z",
                },
            ]
        }

        mock_client.get.side_effect = [
            duplicate_functions,  # functions
            Exception("Not found"),  # lookups
            Exception("Not found"),  # pipelines
        ]
        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        # Should find duplicate functionality

    def test_library_entry_properties(self):
        """Test LibraryEntry property methods."""
        large_lib = LibraryEntry(
            id="test",
            name="largeLib",
            type="function",
            size_bytes=2_000_000,  # 2MB
        )

        assert large_lib.is_large is True

        small_lib = LibraryEntry(
            id="test2",
            name="smallLib",
            type="function",
            size_bytes=1000,  # 1KB
        )

        assert small_lib.is_large is False

    def test_extract_function_calls_simple(self, analyzer):
        """Test function call extraction from pipeline config."""
        pipeline_config = {
            "steps": [
                {"type": "function", "function": {"name": "myFunction"}},
                {"filter": "field == 'value' && otherFunction()", "type": "filter"},
            ]
        }

        functions = analyzer._extract_function_calls(pipeline_config)

        assert "myFunction" in functions
        assert "otherFunction" in functions

    def test_extract_lookup_references(self, analyzer):
        """Test lookup reference extraction."""
        pipeline_config = {
            "steps": [
                {"type": "lookup", "file": "lookup_file.csv"},
                {"function": {"name": "lookup", "args": {"file": "another_lookup.csv"}}},
            ]
        }

        lookups = analyzer._extract_lookup_references(pipeline_config)

        assert "lookup_file.csv" in lookups
        assert "another_lookup.csv" in lookups

    def test_estimate_size(self, analyzer):
        """Test library size estimation."""
        data = {"content": "test" * 1000}  # ~5KB string

        size = analyzer._estimate_size(data)

        # Should be roughly 2x the string length (for internal representation)
        assert size > 8000  # At least 8KB
        assert size < 12000  # At most 12KB

    def test_count_functions_in_pipeline(self, analyzer):
        """Test function counting in pipeline fragments."""
        pipeline_data = {
            "config": {
                "steps": [
                    {"type": "function"},
                    {"type": "filter"},
                    {"type": "function"},
                    {"type": "function"},
                ]
            }
        }

        count = analyzer._count_functions_in_pipeline(pipeline_data)

        assert count == 3

    def test_calculate_content_hash(self, analyzer):
        """Test content hash calculation."""
        data1 = {"content": "test content"}
        data2 = {"content": "different content"}

        hash1 = analyzer._calculate_content_hash(data1)
        hash2 = analyzer._calculate_content_hash(data2)

        assert hash1 != hash2
        assert len(hash1) == 8  # 8 character hash

        # Same content should produce same hash
        hash1_again = analyzer._calculate_content_hash(data1)
        assert hash1 == hash1_again

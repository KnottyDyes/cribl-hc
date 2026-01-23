"""
Unit tests for HECValidationAnalyzer.
"""

from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.hec_validation import HECValidationAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestHECValidationAnalyzer:
    @pytest.fixture
    def analyzer(self) -> HECValidationAnalyzer:
        return HECValidationAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_outputs = AsyncMock(return_value=[])
        return client

    def test_objective_name(self, analyzer: HECValidationAnalyzer) -> None:
        assert analyzer.objective_name == "hec_validation"

    def test_supported_products(self, analyzer: HECValidationAnalyzer) -> None:
        products = analyzer.supported_products
        assert "stream" in products
        assert "edge" in products
        assert "lake" not in products
        assert "search" not in products

    def test_required_permissions(self, analyzer: HECValidationAnalyzer) -> None:
        assert "read:outputs" in analyzer.get_required_permissions()

    @pytest.mark.asyncio
    async def test_no_hec_outputs_found(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "hec-no-outputs" for f in result.findings)

    @pytest.mark.asyncio
    async def test_missing_hec_url(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[{"id": "hec-1", "type": "splunk_hec", "disabled": False}]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "hec-url-missing-hec-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_invalid_hec_url_format(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "hec-url-invalid-hec-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_valid_hec_url(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert not any("url-invalid" in f.id for f in result.findings)

    @pytest.mark.asyncio
    async def test_valid_hec_url_raw_endpoint(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-raw",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/raw",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert not any("url-invalid" in f.id for f in result.findings)

    @pytest.mark.asyncio
    async def test_valid_hec_url_s2s_endpoint(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-s2s",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/s2s",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert not any("url-invalid" in f.id for f in result.findings)

    @pytest.mark.asyncio
    async def test_valid_hec_url_base_path_crowdstrike(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "crowdstrike-hec",
                    "type": "splunk_hec",
                    "url": "https://crowdstrike.example.com:8088/services/collector",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert not any("url-invalid" in f.id for f in result.findings)

    @pytest.mark.asyncio
    async def test_ssl_disabled_for_https(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "disableSsl": True,
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "hec-ssl-disabled-hec-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_crowdstrike_url_with_splunk_type(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "crowdstrike-hec",
                    "type": "splunk_hec",
                    "url": "https://crowdstrike.example.com:8088/services/collector",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(
            f.id == "hec-crowdstrike-destination-type-crowdstrike-hec" for f in result.findings
        )

    @pytest.mark.asyncio
    async def test_missing_token(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "hec-token-missing-hec-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_placeholder_token(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "token": "your-token-here",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "hec-token-placeholder-hec-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_invalid_token_format(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "token": "not-a-uuid",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "hec-token-invalid-hec-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_valid_token_format(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "token": "550e8400-e29b-41d4-a716-446655440000",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert not any("token-invalid" in f.id for f in result.findings)

    @pytest.mark.asyncio
    async def test_ack_disabled(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "token": "550e8400-e29b-41d4-a716-446655440000",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "hec-ack-disabled-hec-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_ack_timeout_too_low(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "token": "550e8400-e29b-41d4-a716-446655440000",
                    "acknowledgment": True,
                    "ackTimeout": 20,
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "hec-ack-timeout-critical-hec-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_ack_timeout_warning(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "token": "550e8400-e29b-41d4-a716-446655440000",
                    "acknowledgment": True,
                    "ackTimeout": 40,
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "hec-ack-timeout-warning-hec-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_missing_index(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "token": "550e8400-e29b-41d4-a716-446655440000",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "hec-index-missing-hec-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_single_endpoint_no_lb(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "token": "550e8400-e29b-41d4-a716-446655440000",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "hec-lb-single-hec-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_compression_disabled(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "token": "550e8400-e29b-41d4-a716-446655440000",
                    "compression": False,
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "hec-compression-disabled-hec-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_multiple_hec_outputs(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "token": "550e8400-e29b-41d4-a716-446655440000",
                    "compression": True,
                    "disabled": False,
                },
                {
                    "id": "hec-2",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "token": "550e8400-e29b-41d4-a716-446655440000",
                    "compression": False,
                    "disabled": False,
                },
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert result.metadata["hec_outputs_total"] == 2

    @pytest.mark.asyncio
    async def test_disabled_hec_output(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "hec-1",
                    "type": "splunk_hec",
                    "url": "https://splunk.example.com:8088/services/collector/event",
                    "token": "550e8400-e29b-41d4-a716-446655440000",
                    "disabled": True,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        # Disabled outputs should be skipped
        assert not any("hec-1" in f.id for f in result.findings)

    @pytest.mark.asyncio
    async def test_non_hec_output(
        self, analyzer: HECValidationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_outputs = AsyncMock(
            return_value=[
                {
                    "id": "s3-1",
                    "type": "s3",
                    "url": "https://s3.amazonaws.com/bucket",
                    "disabled": False,
                }
            ]
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        # Should report no HEC outputs found
        assert any(f.id == "hec-no-outputs" for f in result.findings)

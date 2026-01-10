import pytest
from unittest.mock import AsyncMock

from cribl_hc.analyzers.parser_quality import ParserQualityAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


def create_parser(
    parser_id: str, parser_name: str = "test_parser", regex: str = r"^(\d+)\s(\w+)$"
) -> dict:
    return {
        "id": parser_id,
        "name": parser_name,
        "regex": regex,
        "enabled": True,
    }


def create_parser_metrics(parser_id: str, events: int = 1000, errors: int = 0) -> list:
    return [
        {"dimensions": {"parser": parser_id}, "name": "parser.events", "value": events},
        {"dimensions": {"parser": parser_id}, "name": "parser.errors", "value": errors},
    ]


class TestParserQualityAnalyzer:
    @pytest.fixture
    def mock_client(self):
        client = AsyncMock(spec=CriblAPIClient)
        client.get_parsers = AsyncMock(return_value=[])
        client.get_metrics = AsyncMock(return_value={})
        client.get_pipelines = AsyncMock(return_value=[])
        client.worker_group = "default"
        return client

    @pytest.mark.asyncio
    async def test_healthy_parsers_no_findings(self, mock_client):
        parsers = [create_parser("parser-1"), create_parser("parser-2")]
        metrics = {"items": create_parser_metrics("parser-1") + create_parser_metrics("parser-2")}
        mock_client.get_parsers.return_value = parsers
        mock_client.get_metrics.return_value = metrics

        analyzer = ParserQualityAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 2
        assert result.metadata["parsers_analyzed"] == 2
        assert result.metadata["healthy_parsers"] == 0

    @pytest.mark.asyncio
    async def test_parser_error_rate_high(self, mock_client):
        parsers = [create_parser("parser-err")]
        metrics = {"items": create_parser_metrics("parser-err", events=1000, errors=70)}

        mock_client.get_parsers.return_value = parsers
        mock_client.get_metrics.return_value = metrics

        analyzer = ParserQualityAnalyzer()
        result = await analyzer.analyze(mock_client)

        findings = [f for f in result.findings if f.id.startswith("parser-quality-error")]
        assert len(findings) == 1
        assert findings[0].severity == "high"
        assert "error rate" in findings[0].title.lower()

    @pytest.mark.asyncio
    async def test_parser_error_rate_critical(self, mock_client):
        parsers = [create_parser("parser-bad")]
        metrics = {"items": create_parser_metrics("parser-bad", events=1000, errors=150)}

        mock_client.get_parsers.return_value = parsers
        mock_client.get_metrics.return_value = metrics

        analyzer = ParserQualityAnalyzer()
        result = await analyzer.analyze(mock_client)

        findings = [f for f in result.findings if f.id.startswith("parser-quality-error")]
        assert len(findings) == 1
        assert findings[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_risky_regex_pattern(self, mock_client):
        risky_regex = r"(\w+\*)+test(\w+\+)+"
        parsers = [create_parser("parser-risky", regex=risky_regex)]

        mock_client.get_parsers.return_value = parsers
        mock_client.get_metrics.return_value = {"items": []}

        analyzer = ParserQualityAnalyzer()
        result = await analyzer.analyze(mock_client)

        findings = [f for f in result.findings if "risky" in f.id.lower()]
        assert len(findings) == 1
        assert findings[0].severity == "high"
        assert "regex" in findings[0].title.lower()

    @pytest.mark.asyncio
    async def test_unused_parser(self, mock_client):
        safe_regex = r"^test(\w+)$"
        parsers = [create_parser("parser-unused", regex=safe_regex)]
        pipelines = [{"id": "pipe-1", "functions": []}]

        mock_client.get_parsers.return_value = parsers
        mock_client.get_metrics.return_value = {"items": []}
        mock_client.get_pipelines.return_value = pipelines

        analyzer = ParserQualityAnalyzer()
        result = await analyzer.analyze(mock_client)

        unused_findings = [f for f in result.findings if "unused" in f.id.lower()]
        assert len(unused_findings) >= 1
        assert unused_findings[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_parser_in_use(self, mock_client):
        safe_regex = r"^test(\w+)$"
        parsers = [create_parser("parser-used", regex=safe_regex)]
        pipelines = [
            {
                "id": "pipe-1",
                "functions": [
                    {"id": "func-1", "type": "parser", "args": {"parser": "parser-used"}}
                ],
            }
        ]

        mock_client.get_parsers.return_value = parsers
        mock_client.get_metrics.return_value = {"items": create_parser_metrics("parser-used")}
        mock_client.get_pipelines.return_value = pipelines

        analyzer = ParserQualityAnalyzer()
        result = await analyzer.analyze(mock_client)

        unused_findings = [f for f in result.findings if "unused" in f.id.lower()]
        assert len(unused_findings) == 0

    @pytest.mark.asyncio
    async def test_no_parsers_available(self, mock_client):
        mock_client.get_parsers.return_value = []
        mock_client.get_metrics.return_value = {"items": []}

        analyzer = ParserQualityAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        assert result.findings[0].id == "parser-quality-no-parsers"

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_client):
        mock_client.get_parsers.side_effect = Exception("API Failure")
        mock_client.get_metrics.return_value = {"items": []}

        analyzer = ParserQualityAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        assert result.findings[0].id == "parser-quality-no-parsers"

    @pytest.mark.asyncio
    async def test_multiple_issues_per_parser(self, mock_client):
        risky_regex = r"(\w+\*)+test(\w+\+)+"
        parsers = [create_parser("parser-multi", regex=risky_regex)]
        metrics = {"items": create_parser_metrics("parser-multi", events=1000, errors=70)}
        pipelines = [{"id": "pipe-1", "functions": []}]

        mock_client.get_parsers.return_value = parsers
        mock_client.get_metrics.return_value = metrics
        mock_client.get_pipelines.return_value = pipelines

        analyzer = ParserQualityAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) >= 3

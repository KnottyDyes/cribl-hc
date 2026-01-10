from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.schema_quality import SchemaQualityAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


def create_input(input_id: str, filter_expr: str) -> dict:
    return {
        "id": input_id,
        "filter": filter_expr,
    }


class TestSchemaQualityAnalyzer:
    @pytest.mark.asyncio
    async def test_input_filter_regex_pattern_flagged(self):
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.get_parsers.return_value = []
        mock_client.get_pipelines.return_value = []
        mock_client.get_inputs.return_value = [create_input("input-1", "message =~ /(.+)+/")]
        mock_client.get_search_datatypes.return_value = {"items": []}

        analyzer = SchemaQualityAnalyzer()
        result = await analyzer.analyze(mock_client)

        regex_findings = [
            f for f in result.findings if f.id.startswith("regex-problematic-input:input-1")
        ]
        assert len(regex_findings) == 1
        assert regex_findings[0].severity == "medium"

from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.data.api_football import APIFootballClient


@pytest.mark.asyncio
async def test_get_live_fixtures_uses_provided_api_key() -> None:
    """Ensure a provided API key is used in request headers."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"response": []}
    mock_httpx_client = AsyncMock()
    mock_httpx_client.get = AsyncMock(return_value=response)

    with patch("backend.data.api_football.httpx.AsyncClient", return_value=mock_httpx_client):
        client = APIFootballClient(api_key="override-key")
        await client.get_live_fixtures()

    call_kwargs = mock_httpx_client.get.call_args.kwargs
    assert call_kwargs["headers"]["x-apisports-key"] == "override-key"

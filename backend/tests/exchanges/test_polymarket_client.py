import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.exchanges.polymarket import PolymarketClient
import httpx

@pytest.fixture
def client():
    with patch("httpx.AsyncClient") as mock_http_client:
        client = PolymarketClient()
        # Mock the internal httpx client
        client.client = mock_http_client
        yield client

@pytest.mark.asyncio
async def test_get_markets_by_event_success(client):
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"id": "mkt1", "question": "Test Market"}]
    client.client.get = AsyncMock(return_value=mock_response)

    markets = await client.get_markets_by_event("Test Event")

    assert len(markets) == 1
    assert markets[0]["id"] == "mkt1"
    client.client.get.assert_called_once()

@pytest.mark.asyncio
async def test_get_markets_by_event_failure(client):
    # Mock failure response
    mock_response = MagicMock()
    mock_response.status_code = 500
    client.client.get = AsyncMock(return_value=mock_response)

    markets = await client.get_markets_by_event("Test Event")

    assert markets == []

@pytest.mark.asyncio
async def test_get_orderbook_success(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    # Structure based on PolymarketClient implementation
    mock_response.json.return_value = {
        "bids": [{"price": "0.45", "size": "100"}],
        "asks": [{"price": "0.55", "size": "100"}]
    }
    client.client.get = AsyncMock(return_value=mock_response)

    ob = await client.get_orderbook("token123")

    assert ob is not None
    assert ob["token_id"] == "token123"
    assert ob["best_bid"] == 0.45
    assert ob["best_ask"] == 0.55
    assert ob["mid_price"] == 0.50

@pytest.mark.asyncio
async def test_get_orderbook_empty(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"bids": [], "asks": []}
    client.client.get = AsyncMock(return_value=mock_response)

    ob = await client.get_orderbook("token123")
    assert ob is None

@pytest.mark.asyncio
async def test_get_orderbook_failure(client):
    mock_response = MagicMock()
    mock_response.status_code = 404
    client.client.get = AsyncMock(return_value=mock_response)

    ob = await client.get_orderbook("token123")
    assert ob is None

@pytest.mark.asyncio
async def test_get_yes_price_success(client):
    # Reuse get_orderbook logic logic by mocking get_orderbook method if we wanted,
    # but here we test full flow or mock the internal call.
    # To strictly unit test get_yes_price, we can mock get_orderbook.

    with patch.object(client, "get_orderbook", new_callable=AsyncMock) as mock_get_ob:
        mock_get_ob.return_value = {"best_ask": 0.65}

        price = await client.get_yes_price("token123")
        assert price == 0.65

@pytest.mark.asyncio
async def test_get_yes_price_none(client):
    with patch.object(client, "get_orderbook", new_callable=AsyncMock) as mock_get_ob:
        mock_get_ob.return_value = None

        price = await client.get_yes_price("token123")
        assert price is None

@pytest.mark.asyncio
async def test_place_order_success(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"order_id": "ord123"}
    client.client.post = AsyncMock(return_value=mock_response)

    result = await client.place_order("token123", "BUY", 0.5, 10)

    assert result["order_id"] == "ord123"
    client.client.post.assert_called_once()
    # Check payload
    call_kwargs = client.client.post.call_args[1]
    assert call_kwargs["json"]["token_id"] == "token123"
    assert call_kwargs["json"]["side"] == "BUY"

@pytest.mark.asyncio
async def test_place_order_failure(client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    client.client.post = AsyncMock(return_value=mock_response)

    result = await client.place_order("token123", "BUY", 0.5, 10)
    assert result is None

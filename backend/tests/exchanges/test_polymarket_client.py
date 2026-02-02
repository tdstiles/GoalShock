import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.exchanges.polymarket import PolymarketClient
import httpx

@pytest.fixture
def client():
    with patch("httpx.AsyncClient") as mock_http_client:
        # Patch settings to avoid side effects or relying on env vars
        with patch("backend.exchanges.polymarket.settings") as mock_settings:
            mock_settings.POLYMARKET_PRIVATE_KEY = "test_key"
            mock_settings.POLYMARKET_CHAIN_ID = 137

            # We also need to patch ClobClient init so it doesn't try to actually connect or validate key
            with patch("backend.exchanges.polymarket.ClobClient") as MockClob:
                client = PolymarketClient()
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
async def test_place_order_signed_success(client):
    # Mock ClobClient
    mock_clob = MagicMock()
    client.clob_client = mock_clob

    # Mock return value of create_and_post_order
    mock_clob.create_and_post_order.return_value = {"orderID": "ord123"}

    result = await client.place_order("token123", "BUY", 0.5, 10)

    assert result["orderID"] == "ord123"
    assert result["order_id"] == "ord123"
    mock_clob.create_and_post_order.assert_called_once()

    # Verify OrderArgs
    call_args = mock_clob.create_and_post_order.call_args[0][0]
    assert call_args.token_id == "token123"
    assert call_args.side == "BUY"
    assert call_args.price == 0.5
    assert call_args.size == 10

@pytest.mark.asyncio
async def test_place_order_no_key(client):
    # Simulate missing private key
    client.clob_client = None

    result = await client.place_order("token123", "BUY", 0.5, 10)
    assert result is None

@pytest.mark.asyncio
async def test_place_order_failure_response(client):
    mock_clob = MagicMock()
    client.clob_client = mock_clob

    # Mock failure (no orderID in response)
    mock_clob.create_and_post_order.return_value = {"error": "Insufficient balance"}

    result = await client.place_order("token123", "BUY", 0.5, 10)
    # Our code returns the response even on failure, but logs error.
    # Logic: if response and response.get("orderID") -> OK, else Log Error and Return Response
    assert result == {"error": "Insufficient balance"}

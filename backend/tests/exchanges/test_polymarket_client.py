import pytest
import asyncio
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
                # Mock the instance
                mock_clob_instance = MagicMock()
                MockClob.return_value = mock_clob_instance

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
    # client.clob_client is already mocked by fixture, but we need to configure return value
    mock_clob = client.clob_client

    # Mock return value of create_and_post_order
    mock_clob.create_and_post_order.return_value = {"orderID": "ord123"}

    # Must use patch asyncio.to_thread because place_order uses it
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = {"orderID": "ord123", "order_id": "ord123"}

        # We need to ensure client.clob_client is set (it is by fixture)

        result = await client.place_order("token123", "BUY", 0.5, 10)

        assert result["orderID"] == "ord123"
        assert result["order_id"] == "ord123"
        # Since we mocked to_thread, create_and_post_order won't be called directly in this test scope unless to_thread calls it.
        # But we mocked to_thread return value directly. So we check to_thread call.
        mock_to_thread.assert_called_once()

@pytest.mark.asyncio
async def test_place_order_no_key(client):
    # Simulate missing private key
    client.clob_client = None

    result = await client.place_order("token123", "BUY", 0.5, 10)
    assert result is None

@pytest.mark.asyncio
async def test_place_order_failure_response(client):
    # Mock failure (no orderID in response)
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.return_value = {"error": "Insufficient balance"}

        result = await client.place_order("token123", "BUY", 0.5, 10)
        assert result == {"error": "Insufficient balance"}

@pytest.mark.asyncio
async def test_place_order_wait_fill_timeout_race_condition(client):
    """
    Test that place_order_and_wait_for_fill correctly returns a filled order
    even if the loop times out and cancellation 'fails' (e.g. because it was filled).
    """
    # 1. Mock place_order to return success
    order_response = {"orderID": "ord_race", "status": "OPEN", "order_id": "ord_race"}

    # 2. Mock get_order responses
    open_order = {"orderID": "ord_race", "status": "OPEN"}
    filled_order = {"orderID": "ord_race", "status": "FILLED"}

    # 3. Mock cancel_order to FAIL (return False)
    # This simulates "Order cannot be cancelled because it is already filled"
    client.cancel_order = AsyncMock(return_value=False)

    # 4. Configure get_order side effects
    # Loop runs 2 times (timeout/poll). calls: [OPEN, OPEN]
    # Then final check calls: [FILLED]
    client.get_order = AsyncMock(side_effect=[open_order, open_order, filled_order])

    # Patch place_order to return immediately
    client.place_order = AsyncMock(return_value=order_response)

    # Execution
    result = await client.place_order_and_wait_for_fill(
        token_id="tok_1",
        side="BUY",
        price=0.5,
        size=10.0,
        timeout=0.1,
        poll_interval=0.04
    )

    # Verification
    assert result is not None
    assert result["status"] == "FILLED"
    assert result["orderID"] == "ord_race"

    # Verify cancel was attempted
    client.cancel_order.assert_called_once_with("ord_race")

    # Verify final status check was made (implied by result being filled_order)

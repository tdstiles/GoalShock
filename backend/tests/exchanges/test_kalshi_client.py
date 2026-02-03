import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.exchanges.kalshi import KalshiClient
import httpx

@pytest.fixture
def client():
    with patch("httpx.AsyncClient") as mock_http_client_cls:
        # Create a mock instance that the class will return
        mock_instance = AsyncMock()
        mock_http_client_cls.return_value = mock_instance

        # Patch os.getenv to return dummy keys
        with patch("os.getenv") as mock_getenv:
            def getenv_side_effect(key, default=None):
                if key == "KALSHI_API_KEY": return "test_email"
                if key == "KALSHI_API_SECRET": return "test_pass"
                return default
            mock_getenv.side_effect = getenv_side_effect

            client = KalshiClient()
            yield client

@pytest.mark.asyncio
async def test_login_success(client):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"token": "fake_token_123"}
    client.client.post.return_value = mock_response

    result = await client.login()

    assert result is True
    assert client.auth_token == "fake_token_123"
    client.client.post.assert_called_once()
    # verify url ends with /login
    args, _ = client.client.post.call_args
    assert args[0].endswith("/login")

@pytest.mark.asyncio
async def test_login_failure(client):
    mock_response = MagicMock()
    mock_response.status_code = 401
    client.client.post.return_value = mock_response

    result = await client.login()

    assert result is False
    assert client.auth_token is None

@pytest.mark.asyncio
async def test_get_markets_success(client):
    # Pre-set auth token to avoid login call
    client.auth_token = "existing_token"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "markets": [
            {"ticker": "KXTEST", "title": "Test Market"}
        ]
    }
    client.client.get.return_value = mock_response

    markets = await client.get_markets()

    assert len(markets) == 1
    assert markets[0]["ticker"] == "KXTEST"

    # Verify auth header
    call_kwargs = client.client.get.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer existing_token"

@pytest.mark.asyncio
async def test_get_markets_auto_login(client):
    # No auth token initially
    client.auth_token = None

    # Mock login response
    login_response = MagicMock()
    login_response.status_code = 200
    login_response.json.return_value = {"token": "new_token"}

    # Mock markets response
    markets_response = MagicMock()
    markets_response.status_code = 200
    markets_response.json.return_value = {"markets": []}

    # We need to set side_effect because client.post is called then client.get
    # But wait, they are different methods (post vs get).
    client.client.post.return_value = login_response
    client.client.get.return_value = markets_response

    await client.get_markets()

    assert client.auth_token == "new_token"
    client.client.post.assert_called_once() # Login called
    client.client.get.assert_called_once()  # Markets called

@pytest.mark.asyncio
async def test_get_orderbook_success(client):
    client.auth_token = "token"

    mock_response = MagicMock()
    mock_response.status_code = 200
    # yes_bids: [[price, size], ...]
    # Kalshi format roughly: [[99, 10], [98, 5]] (cents)
    mock_response.json.return_value = {
        "orderbook": {
            "yes": [[60, 100]],
            "no": [[38, 50]]
        }
    }
    client.client.get.return_value = mock_response

    ob = await client.get_orderbook("KXTEST")

    # yes_bid = 60/100 = 0.60
    # yes_ask = (100 - 38)/100 = 0.62

    assert ob is not None
    assert ob["ticker"] == "KXTEST"
    assert ob["yes_bid"] == 0.60
    assert ob["yes_ask"] == 0.62
    # mid = (0.60 + 0.62) / 2 = 0.61
    assert ob["mid_price"] == 0.61

@pytest.mark.asyncio
async def test_get_orderbook_empty(client):
    client.auth_token = "token"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"orderbook": {"yes": [], "no": []}}
    client.client.get.return_value = mock_response

    ob = await client.get_orderbook("KXTEST")
    assert ob is None

@pytest.mark.asyncio
async def test_get_yes_price(client):
    # Mock get_orderbook by patching the method on the instance
    # But since we are testing unit, we can just mock the return of client.client.get
    # effectively testing integration of get_yes_price -> get_orderbook

    client.auth_token = "token"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "orderbook": {
            "yes": [[50, 1]],
            "no": [[45, 1]]
        }
    }
    client.client.get.return_value = mock_response

    price = await client.get_yes_price("KXTEST")

    # yes_ask = (100 - 45) / 100 = 0.55
    assert price == 0.55

@pytest.mark.asyncio
async def test_place_order_success(client):
    client.auth_token = "token"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "order": {
            "order_id": "ord_123"
        }
    }
    client.client.post.return_value = mock_response

    result = await client.place_order(
        ticker="KXTEST",
        side="yes",
        action="buy",
        count=10,
        price=50
    )

    assert result["order_id"] == "ord_123"

    # Check payload
    call_kwargs = client.client.post.call_args.kwargs
    payload = call_kwargs["json"]
    assert payload["ticker"] == "KXTEST"
    assert payload["side"] == "yes"
    assert payload["action"] == "buy"
    assert payload["count"] == 10
    assert payload["yes_price"] == 50
    assert payload["no_price"] is None

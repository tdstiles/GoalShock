import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import os

# Import relative to PYTHONPATH=backend
from core.data_pipeline import DataAcquisitionLayer, PrimaryProviderUnavailableError

@pytest.fixture
def mock_env_primary():
    """Environment variables for primary mode."""
    return {
        "API_FOOTBALL_KEY": "valid_key_over_20_chars_long",
        "POLYMARKET_API_KEY": "poly_key",
        "KALSHI_API_KEY": "kalshi_key",
        "KALSHI_API_SECRET": "kalshi_secret"
    }

@pytest.fixture
def mock_env_auxiliary():
    """Environment variables for auxiliary mode."""
    return {
        "API_FOOTBALL_KEY": "", # Missing
        "POLYMARKET_API_KEY": ""
    }

@pytest.mark.asyncio
async def test_operational_mode_primary(mock_env_primary):
    with patch.dict(os.environ, mock_env_primary):
        dal = DataAcquisitionLayer()
        assert dal._srvc_mode == "primary"

@pytest.mark.asyncio
async def test_operational_mode_auxiliary(mock_env_auxiliary):
    with patch.dict(os.environ, mock_env_auxiliary):
        dal = DataAcquisitionLayer()
        assert dal._srvc_mode == "auxiliary"

@pytest.mark.asyncio
async def test_fetch_live_goals_primary_success(mock_env_primary):
    """Test successful fetching from API Football."""
    with patch.dict(os.environ, mock_env_primary):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client

            # Setup mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": [
                    {
                        "fixture": {"id": 1001},
                        "events": [
                            {
                                "type": "Goal",
                                "team": {"name": "Team A"},
                                "player": {"name": "Player 1"},
                                "time": {"elapsed": 45}
                            }
                        ]
                    }
                ]
            }
            mock_client.get.return_value = mock_response

            dal = DataAcquisitionLayer()
            goals = await dal.fetch_live_goals()

            assert len(goals) == 1
            assert goals[0].match_id == "1001"
            assert goals[0].team == "Team A"
            assert goals[0].player == "Player 1"
            assert goals[0].minute == 45

            mock_client.get.assert_called_once()
            args, kwargs = mock_client.get.call_args
            assert "v3.football.api-sports.io" in args[0]

@pytest.mark.asyncio
async def test_fetch_live_goals_primary_raises_on_failure(mock_env_primary):
    """Test primary mode raises explicit failure instead of synthetic fallback."""
    with patch.dict(os.environ, mock_env_primary):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client

            # Setup mock response to fail
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Error"
            mock_client.get.return_value = mock_response

            dal = DataAcquisitionLayer()

            with patch.object(dal, "_generate_event_stream", wraps=dal._generate_event_stream) as mock_synth:
                with pytest.raises(PrimaryProviderUnavailableError) as exc_info:
                    await dal.fetch_live_goals()

            assert exc_info.value.operation == "fetch_live_goals"
            assert exc_info.value.source == "api_football"
            mock_synth.assert_not_called()

@pytest.mark.asyncio
async def test_fetch_market_data_polymarket(mock_env_primary):
    """Test fetching market data from Polymarket."""
    with patch.dict(os.environ, mock_env_primary):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{"id": "m1", "question": "Q1"}]
            mock_client.get.return_value = mock_response

            dal = DataAcquisitionLayer()
            markets = await dal.fetch_market_data(market_type="football")

            assert markets == [{"id": "m1", "question": "Q1"}]
            assert "api.polymarket.com" in mock_client.get.call_args[0][0]

@pytest.mark.asyncio
async def test_fetch_market_data_kalshi_fallback(mock_env_primary):
    """Test using Kalshi if Polymarket key is missing but Kalshi is present."""
    env = mock_env_primary.copy()
    env["POLYMARKET_API_KEY"] = "" # Disable polymarket

    with patch.dict(os.environ, env):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client

            # Mock Login
            mock_login_resp = MagicMock()
            mock_login_resp.status_code = 200
            mock_login_resp.json.return_value = {"token": "fake_token"}

            # Mock Markets
            mock_markets_resp = MagicMock()
            mock_markets_resp.status_code = 200
            mock_markets_resp.json.return_value = {"markets": []}

            # Handle multiple calls
            mock_client.post.return_value = mock_login_resp
            mock_client.get.return_value = mock_markets_resp

            dal = DataAcquisitionLayer()

            await dal.fetch_market_data()

            mock_client.post.assert_called_once()
            assert "api.kalshi.com/v1/login" in mock_client.post.call_args[0][0]

@pytest.mark.asyncio
async def test_fetch_market_data_auxiliary_uses_simulation():
    """Test auxiliary mode uses synthetic market data by design."""
    with patch.dict(os.environ, {}): # No keys
        dal = DataAcquisitionLayer()
        data = await dal.fetch_market_data()

        assert "markets" in data
        assert data["count"] > 0
        assert data["markets"][0]["yes_price"] > 0


@pytest.mark.asyncio
async def test_fetch_market_data_primary_raises_on_failure(mock_env_primary):
    """Test primary mode market failure raises explicit provider unavailable exception."""
    with patch.dict(os.environ, mock_env_primary):
        dal = DataAcquisitionLayer()
        with patch.object(dal, "_fetch_polymarket_data", side_effect=Exception("provider down")):
            with patch.object(dal, "_generate_market_data", wraps=dal._generate_market_data) as mock_synth:
                with pytest.raises(PrimaryProviderUnavailableError) as exc_info:
                    await dal.fetch_market_data()

            assert exc_info.value.operation == "fetch_market_data"
            assert exc_info.value.source == "polymarket"
            mock_synth.assert_not_called()

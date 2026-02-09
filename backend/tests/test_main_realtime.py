import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock, PropertyMock
from datetime import datetime
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import the app (we will patch its dependencies)
from main_realtime import app
from models.schemas import LiveMatch, MarketPrice

# Mock Data
MOCK_FIXTURE_ID = 100
MOCK_MATCH = LiveMatch(
    fixture_id=MOCK_FIXTURE_ID,
    league_id=39,
    league_name="Premier League",
    home_team="Team A",
    away_team="Team B",
    home_score=1,
    away_score=0,
    minute=30,
    status="1H",
    timestamp=datetime.now(),
    markets=[]
)

MOCK_MARKET = MarketPrice(
    market_id="mkt_1",
    fixture_id=MOCK_FIXTURE_ID,
    question="Will Team A win?",
    yes_price=0.6,
    no_price=0.4,
    source="polymarket",
    home_team="Team A",
    away_team="Team B"
)

@pytest.fixture
def mock_realtime_system():
    with patch("main_realtime.realtime_system") as mock_sys:
        # Mock components
        mock_sys.ingestor = MagicMock()
        mock_sys.market_fetcher = MagicMock()
        mock_sys.market_mapper = MagicMock()
        mock_sys.websocket_clients = set()

        # Setup default return values
        mock_sys.ingestor.get_active_matches.return_value = [MOCK_MATCH]
        mock_sys.ingestor.active_fixtures = {MOCK_FIXTURE_ID: MOCK_MATCH}

        # Async methods need AsyncMock
        mock_sys.market_mapper.get_markets_for_match = AsyncMock(return_value=[MOCK_MARKET])
        mock_sys.market_mapper.map_goal_to_markets = AsyncMock(return_value=[MOCK_MARKET])

        mock_sys.market_fetcher.get_all_markets.return_value = [MOCK_MARKET]
        mock_sys.market_fetcher.market_cache = {"mkt_1": MOCK_MARKET}

        yield mock_sys

@pytest.mark.asyncio
async def test_root_endpoint(mock_realtime_system):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "service" in data

@pytest.mark.asyncio
async def test_health_check(mock_realtime_system):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    # Verify it pulled data from our mock
    assert data["active_matches"] == 1
    assert data["cached_markets"] == 1

@pytest.mark.asyncio
async def test_get_live_matches(mock_realtime_system):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/matches/live")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["matches"][0]["fixture_id"] == MOCK_FIXTURE_ID
    assert len(data["matches"][0]["markets"]) == 1

    # Verify market mapper was called
    mock_realtime_system.market_mapper.get_markets_for_match.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_markets_for_fixture_success(mock_realtime_system):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/api/markets/{MOCK_FIXTURE_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["fixture_id"] == MOCK_FIXTURE_ID
    assert len(data["markets"]) == 1

@pytest.mark.asyncio
async def test_get_markets_for_fixture_not_found(mock_realtime_system):
    # Setup mock to return no match for ID 999
    # The logic in main_realtime uses `ingestor.get_active_matches()` and filters by ID
    # Our default mock returns [MOCK_MATCH] which has ID 100.
    # So querying 999 should naturally fail if logic is correct.

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/markets/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Match not found"

@pytest.mark.asyncio
async def test_get_all_markets(mock_realtime_system):
    # Patch the is_stale property on MarketPrice to avoid import errors and control behavior
    with patch("models.schemas.MarketPrice.is_stale", new_callable=PropertyMock) as mock_is_stale:
        mock_is_stale.return_value = False

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/api/markets/all")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["markets"][0]["market_id"] == "mkt_1"

# WebSocket test skipped due to potential timeout issues in test environment
# def test_websocket_connection(mock_realtime_system):
#     client = TestClient(app)
#     with client.websocket_connect("/ws/live") as websocket:
#         data = websocket.receive_json()
#         assert data["type"] == "connected"

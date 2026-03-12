from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
import pytest

from backend.data.api_football import APIFootballClient, LiveFixture


@pytest.fixture
def api_client():
    return APIFootballClient(api_key="test_key")


@pytest.fixture
def mock_httpx_client():
    mock_client = AsyncMock()
    return mock_client


@pytest.mark.asyncio
async def test_get_live_fixtures_uses_provided_api_key() -> None:
    """Ensure a provided API key is used in request headers."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"response": []}
    mock_httpx_client = AsyncMock()
    mock_httpx_client.get = AsyncMock(return_value=response)

    with patch(
        "backend.data.api_football.httpx.AsyncClient", return_value=mock_httpx_client
    ):
        client = APIFootballClient(api_key="override-key")
        await client.get_live_fixtures()

    call_kwargs = mock_httpx_client.get.call_args.kwargs
    assert call_kwargs["headers"]["x-apisports-key"] == "override-key"


@pytest.mark.asyncio
async def test_get_live_fixtures_success(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    mock_response = Mock()
    mock_response.status_code = 200
    # Simulate a supported league (e.g. 39 for Premier League, if settings.SUPPORTED_LEAGUES contains 39)
    # Using a typical set of values
    api_client.supported_leagues = [39]
    mock_response.json.return_value = {
        "response": [
            {
                "fixture": {"id": 1, "status": {"elapsed": 45, "short": "1H"}},
                "league": {"id": 39, "name": "Premier League"},
                "teams": {"home": {"name": "Arsenal"}, "away": {"name": "Chelsea"}},
                "goals": {"home": 1, "away": 0},
            },
            {
                "fixture": {"id": 2, "status": {"elapsed": 10, "short": "1H"}},
                "league": {"id": 999, "name": "Unsupported League"}, # Should be skipped
                "teams": {"home": {"name": "Team A"}, "away": {"name": "Team B"}},
                "goals": {"home": 0, "away": 0},
            }
        ]
    }
    mock_httpx_client.get.return_value = mock_response

    fixtures = await api_client.get_live_fixtures()

    assert len(fixtures) == 1
    assert fixtures[0].fixture_id == 1
    assert fixtures[0].league_id == 39
    assert fixtures[0].home_team == "Arsenal"
    assert fixtures[0].away_team == "Chelsea"
    assert fixtures[0].home_score == 1
    assert fixtures[0].away_score == 0
    assert fixtures[0].minute == 45
    assert fixtures[0].status == "1H"


@pytest.mark.asyncio
async def test_get_live_fixtures_error_status(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    mock_response = Mock()
    mock_response.status_code = 500
    mock_httpx_client.get.return_value = mock_response

    fixtures = await api_client.get_live_fixtures()
    assert fixtures == []


@pytest.mark.asyncio
async def test_get_live_fixtures_exception(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    mock_httpx_client.get.side_effect = Exception("Network Error")

    fixtures = await api_client.get_live_fixtures()
    assert fixtures == []


@pytest.mark.asyncio
async def test_detect_goals_initial_scores(api_client):
    fixtures = [
        LiveFixture(fixture_id=1, league_id=39, league_name="EPL", home_team="A", away_team="B", home_score=1, away_score=0, minute=10, status="1H", timestamp=datetime.now())
    ]
    goals = await api_client.detect_goals(fixtures)
    assert len(goals) == 0
    assert api_client.previous_scores[1] == (1, 0)


@pytest.mark.asyncio
async def test_detect_goals_new_goals(api_client):
    api_client.previous_scores[1] = (1, 0)

    fixtures = [
        LiveFixture(fixture_id=1, league_id=39, league_name="EPL", home_team="A", away_team="B", home_score=2, away_score=1, minute=15, status="1H", timestamp=datetime.now())
    ]
    goals = await api_client.detect_goals(fixtures)

    assert len(goals) == 2
    assert goals[0].team == "A"
    assert goals[0].home_score == 2
    assert goals[0].away_score == 1
    assert goals[1].team == "B"
    assert goals[1].home_score == 2
    assert goals[1].away_score == 1
    assert api_client.previous_scores[1] == (2, 1)


@pytest.mark.asyncio
async def test_get_pre_match_odds_success(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": [
            {
                "bookmakers": [
                    {
                        "bets": [
                            {
                                "name": "Match Winner",
                                "values": [
                                    {"value": "Home", "odd": "1.50"},
                                    {"value": "Draw", "odd": "3.00"},
                                    {"value": "Away", "odd": "4.00"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    mock_httpx_client.get.return_value = mock_response

    odds = await api_client.get_pre_match_odds(1)

    assert odds is not None
    assert odds["Home"] == 1 / 1.50
    assert odds["Draw"] == 1 / 3.00
    assert odds["Away"] == 1 / 4.00


@pytest.mark.asyncio
async def test_get_pre_match_odds_no_match_winner(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": [
            {
                "bookmakers": [
                    {
                        "bets": [
                            {
                                "name": "Over/Under",
                                "values": [
                                    {"value": "Over 2.5", "odd": "1.50"},
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    mock_httpx_client.get.return_value = mock_response

    odds = await api_client.get_pre_match_odds(1)
    assert odds is None


@pytest.mark.asyncio
async def test_get_pre_match_odds_empty_response(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": []}
    mock_httpx_client.get.return_value = mock_response

    odds = await api_client.get_pre_match_odds(1)
    assert odds is None


@pytest.mark.asyncio
async def test_get_pre_match_odds_error_status(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    mock_response = Mock()
    mock_response.status_code = 404
    mock_httpx_client.get.return_value = mock_response

    odds = await api_client.get_pre_match_odds(1)
    assert odds is None


@pytest.mark.asyncio
async def test_get_pre_match_odds_exception(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    mock_httpx_client.get.side_effect = Exception("Error fetching odds")

    odds = await api_client.get_pre_match_odds(1)
    assert odds is None


@pytest.mark.asyncio
async def test_get_fixture_details_success(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": [{"fixture": {"id": 1, "date": "2023-01-01T00:00:00+00:00"}}]
    }
    mock_httpx_client.get.return_value = mock_response

    details = await api_client.get_fixture_details(1)
    assert details is not None
    assert details["fixture"]["id"] == 1


@pytest.mark.asyncio
async def test_get_fixture_details_empty(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": []}
    mock_httpx_client.get.return_value = mock_response

    details = await api_client.get_fixture_details(1)
    assert details is None


@pytest.mark.asyncio
async def test_get_fixture_details_error_status(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    mock_response = Mock()
    mock_response.status_code = 500
    mock_httpx_client.get.return_value = mock_response

    details = await api_client.get_fixture_details(1)
    assert details is None


@pytest.mark.asyncio
async def test_get_fixture_details_exception(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    mock_httpx_client.get.side_effect = Exception("Network Error")

    details = await api_client.get_fixture_details(1)
    assert details is None


@pytest.mark.asyncio
async def test_close(api_client, mock_httpx_client):
    api_client.client = mock_httpx_client
    await api_client.close()
    mock_httpx_client.aclose.assert_awaited_once()

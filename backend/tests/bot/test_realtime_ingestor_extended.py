import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from backend.bot.realtime_ingestor import RealtimeIngestor


@pytest.fixture
def ingestor():
    return RealtimeIngestor()


@pytest.mark.asyncio
async def test_start_unconfigured(ingestor):
    config_patch = patch(
        "backend.config.settings.settings.is_configured", return_value=False
    )
    with config_patch:
        warn_patch = patch("backend.bot.realtime_ingestor.logger.warning")
        with warn_patch as mock_warn:
            await ingestor.start()
            assert not ingestor.running
            mock_warn.assert_called_once_with(
                "API-Football key not configured - using fallback mode"
            )


@pytest.mark.asyncio
async def test_start_configured(ingestor):
    config_patch = patch(
        "backend.config.settings.settings.is_configured", return_value=True
    )
    with config_patch:
        task_patch = patch("backend.bot.realtime_ingestor.asyncio.create_task")
        with task_patch as mock_create_task:
            await ingestor.start()
            assert ingestor.running
            mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_stop(ingestor):
    ingestor.running = True
    ingestor.client = AsyncMock()
    await ingestor.stop()
    assert not ingestor.running
    ingestor.client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_live_fixtures_success(ingestor):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": [
            {"league": {"id": 39}, "fixture": {"id": 1}},
            {"league": {"id": 999}, "fixture": {"id": 2}},
        ]
    }

    ingestor.client.get = AsyncMock(return_value=mock_response)

    leagues_patch = patch(
        "backend.config.settings.settings.SUPPORTED_LEAGUES", [39]
    )
    with leagues_patch:
        fixtures = await ingestor._fetch_live_fixtures()
        assert len(fixtures) == 1
        assert fixtures[0]["fixture"]["id"] == 1


@pytest.mark.asyncio
async def test_fetch_live_fixtures_failure(ingestor):
    mock_response = MagicMock()
    mock_response.status_code = 500
    ingestor.client.get = AsyncMock(return_value=mock_response)

    fixtures = await ingestor._fetch_live_fixtures()
    assert len(fixtures) == 0


@pytest.mark.asyncio
async def test_process_fixtures_new_fixture(ingestor):
    fixture_data = {
        "fixture": {"id": 1, "status": {"elapsed": 10, "short": "1H"}},
        "league": {"id": 39, "name": "Premier League"},
        "teams": {"home": {"name": "Arsenal"}, "away": {"name": "Chelsea"}},
        "goals": {"home": 0, "away": 0},
    }

    await ingestor._process_fixtures([fixture_data])

    assert 1 in ingestor.active_fixtures
    match = ingestor.active_fixtures[1]
    assert match.home_team == "Arsenal"
    assert match.home_score == 0


@pytest.mark.asyncio
async def test_process_fixtures_existing_fixture_with_goal(ingestor):
    fixture_data_1 = {
        "fixture": {"id": 1, "status": {"elapsed": 10, "short": "1H"}},
        "league": {"id": 39, "name": "Premier League"},
        "teams": {"home": {"name": "Arsenal"}, "away": {"name": "Chelsea"}},
        "goals": {"home": 0, "away": 0},
    }

    fixture_data_2 = {
        "fixture": {"id": 1, "status": {"elapsed": 12, "short": "1H"}},
        "league": {"id": 39, "name": "Premier League"},
        "teams": {"home": {"name": "Arsenal"}, "away": {"name": "Chelsea"}},
        "goals": {"home": 1, "away": 0},
    }

    mock_goal = MagicMock()
    ingestor._detect_new_goals = MagicMock(return_value=[mock_goal])
    ingestor._notify_goal = AsyncMock()

    await ingestor._process_fixtures([fixture_data_1])
    await ingestor._process_fixtures([fixture_data_2])

    assert ingestor.active_fixtures[1].home_score == 1
    ingestor._detect_new_goals.assert_called_once()
    ingestor._notify_goal.assert_awaited_once_with(mock_goal)


@pytest.mark.asyncio
async def test_notify_goal_sync_callback(ingestor):
    mock_goal = MagicMock()
    mock_goal.player = "Test Player"
    mock_goal.team = "Test Team"
    mock_goal.minute = 10
    mock_goal.home_team = "Home"
    mock_goal.home_score = 1
    mock_goal.away_score = 0
    mock_goal.away_team = "Away"

    mock_callback = MagicMock()
    mock_callback.__name__ = "mock_callback"
    ingestor.register_goal_callback(mock_callback)

    await ingestor._notify_goal(mock_goal)

    mock_callback.assert_called_once_with(mock_goal)


@pytest.mark.asyncio
async def test_poll_live_matches_success(ingestor):
    ingestor.running = True
    ingestor._rate_limit = AsyncMock()
    fetch_patch = AsyncMock(return_value=[{"fixture": {"id": 1}}])
    ingestor._fetch_live_fixtures = fetch_patch
    ingestor._process_fixtures = AsyncMock()

    async def mock_sleep(seconds):
        ingestor.running = False

    sleep_patch = patch(
        "backend.bot.realtime_ingestor.asyncio.sleep", side_effect=mock_sleep
    )
    with sleep_patch:
        await ingestor._poll_live_matches()

    ingestor._fetch_live_fixtures.assert_awaited_once()
    ingestor._process_fixtures.assert_awaited_once_with(
        [{"fixture": {"id": 1}}]
    )


@pytest.mark.asyncio
async def test_rate_limit(ingestor):
    with patch("backend.bot.realtime_ingestor.datetime") as mock_datetime:
        # Simulate last request was just now, so elapsed is 0
        mock_now1 = datetime(2024, 1, 1, 12, 0, 0)
        ingestor.last_request_time = mock_now1

        # When checking elapsed, it's 0 seconds later
        mock_now2 = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.side_effect = [mock_now2, mock_now2]

        delay_patch = patch(
            "backend.config.settings.settings.REQUEST_DELAY_MS", 1000
        )
        with delay_patch:
            sleep_patch = patch("backend.bot.realtime_ingestor.asyncio.sleep")
            with sleep_patch as mock_sleep:
                await ingestor._rate_limit()
                # 1000ms / 1000 - 0 = 1.0
                mock_sleep.assert_awaited_once_with(1.0)


@pytest.mark.asyncio
async def test_notify_goal_async_callback(ingestor):
    mock_goal = MagicMock()
    mock_goal.player = "Test Player"
    mock_goal.team = "Test Team"
    mock_goal.minute = 10
    mock_goal.home_team = "Home"
    mock_goal.home_score = 1
    mock_goal.away_score = 0
    mock_goal.away_team = "Away"

    mock_callback = AsyncMock()
    mock_callback.__name__ = "mock_callback"
    ingestor.register_goal_callback(mock_callback)

    coro_patch = patch(
        "backend.bot.realtime_ingestor.asyncio.iscoroutinefunction",
        return_value=True,
    )
    with coro_patch:
        await ingestor._notify_goal(mock_goal)

    mock_callback.assert_awaited_once_with(mock_goal)


def test_get_active_matches(ingestor):
    match1 = MagicMock()
    match2 = MagicMock()
    ingestor.active_fixtures = {1: match1, 2: match2}

    matches = ingestor.get_active_matches()
    assert len(matches) == 2
    assert match1 in matches
    assert match2 in matches

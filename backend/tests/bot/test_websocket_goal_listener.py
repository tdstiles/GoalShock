import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from backend.bot.websocket_goal_listener import WebSocketGoalListener, GoalEventWS
from backend.data.api_football import LiveFixture, Goal

# Mock supported league ID
SUPPORTED_LEAGUE_ID = 39 # Premier League

@pytest.fixture
def listener():
    with patch("backend.bot.websocket_goal_listener.APIFootballClient") as MockClient:
        listener = WebSocketGoalListener(api_key="test_key")
        # Ensure client mock is accessible
        listener.client = MockClient.return_value
        return listener

@pytest.mark.asyncio
async def test_poll_cycle_detects_goal(listener):
    """Test that polling cycle detects a goal and triggers callbacks."""

    # Arrange
    callback = AsyncMock()
    callback.__name__ = "async_callback"
    listener.register_goal_callback(callback)

    # Mock fixture data
    fixture = LiveFixture(
        fixture_id=1001,
        league_id=SUPPORTED_LEAGUE_ID,
        league_name="Premier League",
        home_team="Team A",
        away_team="Team B",
        home_score=1,
        away_score=0,
        minute=15,
        status="1H",
        timestamp=datetime.now()
    )

    # Mock detected goal
    detected_goal = Goal(
        fixture_id=1001,
        team="Team A",
        player="Player 1",
        minute=15,
        home_score=1,
        away_score=0
    )

    # Setup client mocks
    listener.client.get_live_fixtures = AsyncMock(return_value=[fixture])
    listener.client.detect_goals = AsyncMock(return_value=[detected_goal])

    # Act
    await listener._poll_cycle()

    # Assert
    assert callback.call_count == 1
    call_args = callback.call_args[0][0]
    assert isinstance(call_args, GoalEventWS)
    assert call_args.fixture_id == 1001
    assert call_args.player == "Player 1"
    assert call_args.home_score == 1
    assert call_args.away_score == 0
    assert call_args.minute == 15

@pytest.mark.asyncio
async def test_poll_cycle_no_goals(listener):
    """Test that polling cycle triggers no callbacks if no goals detected."""

    # Arrange
    callback = AsyncMock()
    callback.__name__ = "async_callback"
    listener.register_goal_callback(callback)

    fixture = LiveFixture(
        fixture_id=1001,
        league_id=SUPPORTED_LEAGUE_ID,
        league_name="Premier League",
        home_team="Team A",
        away_team="Team B",
        home_score=0,
        away_score=0,
        minute=10,
        status="1H",
        timestamp=datetime.now()
    )

    listener.client.get_live_fixtures = AsyncMock(return_value=[fixture])
    listener.client.detect_goals = AsyncMock(return_value=[]) # No new goals

    # Act
    await listener._poll_cycle()

    # Assert
    callback.assert_not_called()
    # But fixture should be in active list
    assert 1001 in listener.active_fixtures

@pytest.mark.asyncio
async def test_poll_cycle_empty_response(listener):
    """Test that empty fixture list is handled gracefully and cleans up stale fixtures."""

    # Pre-populate with a fixture that should be removed
    stale_fixture = LiveFixture(
        fixture_id=999, league_id=1, league_name="Old",
        home_team="A", away_team="B", home_score=0, away_score=0,
        minute=90, status="FT", timestamp=datetime.now()
    )
    listener.active_fixtures[999] = stale_fixture

    listener.client.get_live_fixtures = AsyncMock(return_value=[])

    await listener._poll_cycle()

    assert len(listener.active_fixtures) == 0

@pytest.mark.asyncio
async def test_notify_multiple_callbacks(listener):
    """Test that all registered callbacks are notified."""

    cb1 = AsyncMock()
    cb1.__name__ = "async_callback"
    cb2 = Mock() # Synchronous callback
    cb2.__name__ = "sync_callback"

    listener.register_goal_callback(cb1)
    listener.register_goal_callback(cb2)

    event = GoalEventWS(
        fixture_id=1, league_id=1, league_name="L", home_team="H", away_team="A",
        team="H", player="P", minute=1, home_score=1, away_score=0, goal_type="G",
        timestamp=datetime.now()
    )

    await listener._notify_goal_callbacks(event)

    cb1.assert_called_once_with(event)
    cb2.assert_called_once_with(event)

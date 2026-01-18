import pytest
import asyncio
import json
import logging
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from bot.websocket_goal_listener import (
    WebSocketGoalListener,
    GoalEventWS,
    HybridGoalListener,
)

# Mock supported league ID
SUPPORTED_LEAGUE_ID = 39  # Premier League


@pytest.fixture
def listener():
    listener = WebSocketGoalListener(api_key="test_key")
    # Reset seen_goals for each test
    listener.seen_goals = set()
    return listener


@pytest.mark.asyncio
async def test_process_valid_goal_message(listener):
    """Test that a valid goal message is processed and triggers callbacks."""

    # Arrange
    callback = AsyncMock()
    listener.register_goal_callback(callback)

    message_data = {
        "type": "goal",
        "fixture": {"id": 1001, "home_team": "Team A", "away_team": "Team B"},
        "league": {"id": SUPPORTED_LEAGUE_ID, "name": "Premier League"},
        "goal": {
            "team": "Team A",
            "player": "Player 1",
            "minute": 15,
            "type": "Normal",
        },
        "score": {"home": 1, "away": 0},
    }
    json_message = json.dumps(message_data)

    # Act
    await listener._process_message(json_message)

    # Assert
    assert callback.call_count == 1
    call_args = callback.call_args[0][0]
    assert isinstance(call_args, GoalEventWS)
    assert call_args.fixture_id == 1001
    assert call_args.player == "Player 1"
    assert call_args.home_score == 1
    assert call_args.away_score == 0


@pytest.mark.asyncio
async def test_ignore_unsupported_league(listener):
    """Test that goals from unsupported leagues are ignored."""

    # Arrange
    callback = AsyncMock()
    listener.register_goal_callback(callback)

    UNSUPPORTED_LEAGUE_ID = 9999
    message_data = {
        "type": "goal",
        "fixture": {"id": 1002},
        "league": {"id": UNSUPPORTED_LEAGUE_ID, "name": "Unknown League"},
        "goal": {
            "team": "Team C",
            "player": "Player 2",
            "minute": 20,
            "type": "Normal",
        },
        "score": {"home": 0, "away": 1},
    }
    json_message = json.dumps(message_data)

    # Act
    await listener._process_message(json_message)

    # Assert
    callback.assert_not_called()


@pytest.mark.asyncio
async def test_goal_deduplication(listener):
    """Test that duplicate goal messages are ignored."""

    # Arrange
    callback = AsyncMock()
    listener.register_goal_callback(callback)

    message_data = {
        "type": "goal",
        "fixture": {"id": 1003, "home_team": "Team D", "away_team": "Team E"},
        "league": {"id": SUPPORTED_LEAGUE_ID, "name": "Premier League"},
        "goal": {
            "team": "Team D",
            "player": "Player 3",
            "minute": 30,
            "type": "Normal",
        },
        "score": {"home": 1, "away": 0},
    }
    json_message = json.dumps(message_data)

    # Act
    # First message should trigger callback
    await listener._process_message(json_message)
    assert callback.call_count == 1

    # Second message (identical) should be ignored
    await listener._process_message(json_message)
    assert callback.call_count == 1


@pytest.mark.asyncio
async def test_malformed_json_handled_gracefully(listener):
    """Test that malformed JSON does not crash the listener."""

    # Arrange
    callback = AsyncMock()
    listener.register_goal_callback(callback)

    malformed_message = "this is not json"

    # Act
    try:
        await listener._process_message(malformed_message)
    except Exception as e:
        pytest.fail(f"Listener raised exception on malformed JSON: {e}")

    # Assert
    callback.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_message_type(listener):
    """Test that unknown message types are ignored."""

    # Arrange
    callback = AsyncMock()
    listener.register_goal_callback(callback)

    message_data = {"type": "unknown_type", "data": "some data"}
    json_message = json.dumps(message_data)

    # Act
    await listener._process_message(json_message)

    # Assert
    callback.assert_not_called()


@pytest.mark.asyncio
async def test_fixture_update_handling(listener):
    """Test processing of fixture update messages."""

    # Arrange
    message_data = {"type": "fixture_update", "fixture": {"id": 2001}, "status": "HT"}
    json_message = json.dumps(message_data)

    # Act
    await listener._process_message(json_message)

    # Assert
    assert 2001 in listener.active_fixtures
    assert listener.active_fixtures[2001]["status"] == "HT"


@pytest.mark.asyncio
async def test_notify_goal_callbacks_handles_sync_async_and_errors(listener, caplog):
    """Test goal callback dispatch for sync, async, and failing callbacks."""
    calls = []

    def sync_callback(goal_event):
        calls.append(("sync", goal_event.fixture_id))

    async def async_callback(goal_event):
        calls.append(("async", goal_event.fixture_id))

    def error_callback(_goal_event):
        raise ValueError("boom")

    listener.register_goal_callback(sync_callback)
    listener.register_goal_callback(async_callback)
    listener.register_goal_callback(error_callback)

    goal_event = GoalEventWS(
        fixture_id=999,
        league_id=SUPPORTED_LEAGUE_ID,
        league_name="Premier League",
        home_team="Team A",
        away_team="Team B",
        team="Team A",
        player="Player 1",
        minute=12,
        home_score=1,
        away_score=0,
        goal_type="Normal",
        timestamp=datetime.now(),
    )

    caplog.set_level(logging.ERROR)
    await listener._notify_goal_callbacks(goal_event)

    assert ("sync", 999) in calls
    assert ("async", 999) in calls
    assert "Goal callback error" in caplog.text


@pytest.mark.asyncio
async def test_emit_polling_goal_dispatches_callbacks():
    """Test polling goal events dispatch to registered callbacks."""
    listener = HybridGoalListener(api_key="test_key")

    async_callback = AsyncMock()
    sync_callback = Mock()

    listener.goal_callbacks.append(async_callback)
    listener.goal_callbacks.append(sync_callback)

    fixture = {
        "fixture": {"id": 123, "status": {"elapsed": 55}},
        "league": {"id": SUPPORTED_LEAGUE_ID, "name": "Premier League"},
        "teams": {"home": {"name": "Team A"}, "away": {"name": "Team B"}},
        "goals": {"home": 1, "away": 0},
    }

    try:
        await listener._emit_polling_goal(fixture, "home")
    finally:
        await listener.http_client.aclose()

    assert async_callback.call_count == 1
    assert sync_callback.call_count == 1

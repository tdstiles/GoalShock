"""Tests for websocket goal listener constants and trimming behavior."""

from __future__ import annotations

from typing import Set

import pytest

from backend.bot import websocket_goal_listener as listener_module


@pytest.mark.asyncio
async def test_goal_listener_uses_reconnect_constants() -> None:
    """Ensure instance attributes are initialized from module constants."""
    listener = listener_module.WebSocketGoalListener(api_key="test")

    assert listener.max_reconnect_attempts == listener_module.MAX_RECONNECT_ATTEMPTS
    assert listener.base_reconnect_delay == listener_module.BASE_RECONNECT_DELAY_SECONDS
    assert listener.max_reconnect_delay == listener_module.MAX_RECONNECT_DELAY_SECONDS


@pytest.mark.asyncio
async def test_goal_listener_trims_seen_goals() -> None:
    """Verify seen goals are trimmed to the configured maximum."""
    listener = listener_module.WebSocketGoalListener(api_key="test")
    listener.seen_goals = _build_goal_ids(listener_module.MAX_SEEN_GOALS)

    data = {
        "type": "goal",
        "fixture": {"id": 99, "home_team": "Home", "away_team": "Away"},
        "league": {
            "id": next(iter(listener_module.WebSocketGoalListener.SUPPORTED_LEAGUES)),
            "name": "Test League",
        },
        "goal": {"minute": 12, "player": "Tester", "team": "Home"},
        "score": {"home": 1, "away": 0},
    }

    await listener._handle_goal_event(data)

    assert len(listener.seen_goals) == listener_module.SEEN_GOALS_TRIM_TO


def _build_goal_ids(count: int) -> Set[str]:
    """Build a set of synthetic goal IDs."""
    return {f"fixture_{index}_minute_{index}_player_{index}" for index in range(count)}

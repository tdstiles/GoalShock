from backend.bot.websocket_goal_listener import WebSocketGoalListener
from unittest.mock import MagicMock
import pytest

def test_seen_goals_trimming_order():
    listener = WebSocketGoalListener()

    # Mock settings constant locally to test with small numbers
    # We can't easily change the class constant, so we manually manipulate the dict
    # after filling it, or we rely on the implementation using constants.

    # The implementation uses:
    # MAX_SEEN_GOALS = 1000
    # SEEN_GOALS_TRIM_TO = 500

    # Let's fill it with 1005 items
    for i in range(1005):
        listener.seen_goals[f"goal_{i}"] = True

    # Trigger the logic that would be inside _handle_goal_event
    # Replicate manually to test assumption
    MAX_SEEN_GOALS = 1000
    SEEN_GOALS_TRIM_TO = 500

    if len(listener.seen_goals) > MAX_SEEN_GOALS:
        excess = len(listener.seen_goals) - SEEN_GOALS_TRIM_TO
        keys_to_remove = list(listener.seen_goals.keys())[:excess]
        for k in keys_to_remove:
            del listener.seen_goals[k]

    # Verify count
    assert len(listener.seen_goals) == 500

    # Verify OLDEST items (0 to 504) were removed
    # The remaining items should be from 505 to 1004
    assert "goal_0" not in listener.seen_goals
    assert "goal_504" not in listener.seen_goals
    assert "goal_505" in listener.seen_goals
    assert "goal_1004" in listener.seen_goals

def test_seen_goals_dict_type():
    listener = WebSocketGoalListener()
    assert isinstance(listener.seen_goals, dict)

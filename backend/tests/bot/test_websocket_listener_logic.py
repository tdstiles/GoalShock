
import pytest
from backend.bot.websocket_goal_listener import WebSocketGoalListener

class TestWebSocketGoalListenerLogic:

    @pytest.mark.asyncio
    async def test_handle_goal_event_trimming(self):
        """
        Verify that _handle_goal_event correctly trims the seen_goals dictionary.
        """
        listener = WebSocketGoalListener()
        # Mocking callbacks to avoid errors
        listener.goal_callbacks = []

        # We need to reach MAX_SEEN_GOALS (1000).
        # We will manually populate seen_goals up to 1000
        for i in range(1000):
            listener.seen_goals[f"goal_{i}"] = True

        # Verify initial state
        assert len(listener.seen_goals) == 1000
        assert "goal_0" in listener.seen_goals # Oldest
        assert "goal_999" in listener.seen_goals # Newest

        # Now trigger one more event via _handle_goal_event
        # We need a minimal valid payload
        new_goal_id = "goal_1000"
        payload = {
            "type": "goal",
            "fixture": {"id": 100, "home_team": "H", "away_team": "A"},
            "league": {"id": 39, "name": "PL"}, # 39 is in supported leagues
            "goal": {"minute": 90, "player": "Sherlock", "team": "H"},
            "score": {"home": 1, "away": 0}
        }

        # The goal_id constructed in the method is f"{fixture_id}_{minute}_{player}"
        expected_new_id = "100_90_Sherlock"

        # We need to make sure this ID is NOT in the existing set
        assert expected_new_id not in listener.seen_goals

        await listener._handle_goal_event(payload)

        # Check constants
        from backend.bot.websocket_goal_listener import SEEN_GOALS_TRIM_TO

        assert len(listener.seen_goals) == SEEN_GOALS_TRIM_TO

        # Key Assertion: The NEWEST goal must be present
        assert expected_new_id in listener.seen_goals

        # Key Assertion: The PREVIOUS newest goals (999, 998...) should be preserved up to 499 of them.
        # The OLDEST goals (0, 1, 2...) should be gone.

        assert "goal_0" not in listener.seen_goals
        assert "goal_100" not in listener.seen_goals

        # goal_999 was the last one added before the trigger.
        # It should definitely be kept.
        assert "goal_999" in listener.seen_goals

        # goal_501 should be retained as it's within the recent 500 items (along with new one)
        # 1001 items total. Keep 500. Remove 501.
        # Removed indices: 0..500.
        # Kept indices: 501..1000 (which is the new one).

        assert "goal_500" not in listener.seen_goals, "goal_500 should be removed"
        assert "goal_501" in listener.seen_goals, "goal_501 should be retained"

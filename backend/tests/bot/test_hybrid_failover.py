import pytest
import asyncio
from unittest.mock import MagicMock, patch
from backend.bot.websocket_goal_listener import HybridGoalListener

@pytest.mark.asyncio
async def test_hybrid_listener_fails_over_on_max_retries():
    # Setup
    hybrid = HybridGoalListener(api_key="test")

    # Configure listener to fail fast
    hybrid.ws_listener.max_reconnect_attempts = 2
    hybrid.ws_listener.base_reconnect_delay = 0.01

    # Mock connect to always fail
    # We mock websockets.connect to raise an Exception every time
    with patch("websockets.connect", side_effect=Exception("Connection failed")):

        # Simulate that the hybrid listener has been started
        hybrid.running = True

        # Run _run_websocket directly to simulate the task behavior
        # It should catch the exceptions internally in ws_listener.start()
        # and eventually return when max retries are reached.
        await hybrid._run_websocket()

    # ASSERTION:
    # Current behavior (Bug): start() returns cleanly after max retries, so use_polling_fallback remains False.
    # Desired behavior (Fix): use_polling_fallback should be True.

    # If the bug is present, this assertion will FAIL (fallback is False).
    # Since I am writing a reproduction test, I expect this to fail initially if I assert True.
    # But to "Prove the Case", I usually write the test to FAIL if the bug is present.
    # However, for the tool workflow, I will write the assertion that EXPECTS the FIX.

    assert hybrid.use_polling_fallback is True, "Hybrid listener failed to switch to polling fallback after WS max retries"

import asyncio
import pytest
import os
import logging
from unittest.mock import AsyncMock, MagicMock
from backend.engine_unified import UnifiedTradingEngine, EngineConfig, TradingMode

class SlowPolymarket(AsyncMock):
    async def get_markets_by_event(self, *args, **kwargs):
        # Simulate work
        try:
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            # If cancelled, just re-raise.
            raise

        # Check if closed
        if getattr(self, 'is_closed', False):
             raise RuntimeError("Client is closed!")
        return []

    async def get_yes_price(self, *args, **kwargs):
        return 0.5

    async def close(self):
        self.is_closed = True

@pytest.mark.asyncio
async def test_shutdown_race_condition(caplog):
    # Ensure logs dir exists (fix for previous error)
    os.makedirs("logs", exist_ok=True)

    config = EngineConfig(
        mode=TradingMode.SIMULATION,
        enable_alpha_one=False,
        enable_alpha_two=True,
        enable_websocket=False,
        api_football_key="test",
        polymarket_key="test"
    )

    engine = UnifiedTradingEngine(config)

    engine.api_football = AsyncMock()
    dummy_fixture = MagicMock()
    dummy_fixture.fixture_id = 123
    dummy_fixture.home_team = "Home"
    dummy_fixture.away_team = "Away"
    engine.api_football.get_live_fixtures.return_value = [dummy_fixture]

    engine.polymarket = SlowPolymarket()
    engine.alpha_two = AsyncMock()
    engine.alpha_two.feed_live_fixture_update = AsyncMock()
    engine.alpha_two.stop = AsyncMock()
    engine.alpha_two.export_event_log = MagicMock()

    start_task = asyncio.create_task(engine.start())

    # Wait for loop to enter SlowPolymarket work
    await asyncio.sleep(0.1)

    # Verify engine is running
    assert engine.running

    # Call stop. This should cancel the tasks.
    # If the fix works, SlowPolymarket task is cancelled while sleeping, exits, and never hits the "Client is closed!" check.
    # Also engine.stop() should return quickly.
    await engine.stop()

    # Wait for start_task to finish
    try:
        await asyncio.wait_for(start_task, timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail("Engine shutdown timed out! Background tasks were probably not cancelled.")

    # Check if "Client is closed!" was logged as an error
    error_logs = [r.message for r in caplog.records if r.levelname == 'ERROR']
    assert not any("Client is closed!" in msg for msg in error_logs), f"Race condition detected: Errors logged: {error_logs}"

    assert not engine.running

import pytest
import os
import argparse
from unittest.mock import MagicMock, AsyncMock, patch
from backend.core.data_pipeline import DataAcquisitionLayer, PrimaryProviderUnavailableError
from backend.exchanges.kalshi import KalshiClient
from backend.engine_unified import parse_cli_args, build_engine_config_from_cli_args, EngineConfig, UnifiedTradingEngine, TradingMode, KEY_YES, KEY_NO

# --- BUG #1: Data Pipeline Failure Fallback ---

@pytest.mark.asyncio
async def test_bug_1_primary_mode_failure_raises_exception():
    """
    Verify that Primary mode failures raise an exception instead of silently
    falling back to synthetic data (which was the bug).
    """
    mock_env = {
        "API_FOOTBALL_KEY": "valid_key_over_20_chars_long",
        "POLYMARKET_API_KEY": "poly_key",
        "KALSHI_API_KEY": "kalshi_key",
        "KALSHI_API_SECRET": "kalshi_secret"
    }

    with patch.dict(os.environ, mock_env):
        dal = DataAcquisitionLayer()
        assert dal._srvc_mode == "primary"

        # Mock fetch_live_goals to simulate failure
        with patch.object(dal, "_fetch_verified_goals", side_effect=Exception("API Down")):
            # Ensure generate_event_stream is NOT called (no fallback)
            with patch.object(dal, "_generate_event_stream") as mock_fallback:
                with pytest.raises(PrimaryProviderUnavailableError):
                    await dal.fetch_live_goals()

                mock_fallback.assert_not_called()

# --- BUG #2: Kalshi Client Auth Failure ---

@pytest.mark.asyncio
async def test_bug_2_kalshi_auth_failure_does_not_send_request():
    """
    Verify that Kalshi client stops execution if login fails, instead of
    sending requests with 'Bearer None' (which was the bug).
    """
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_client_cls.return_value = mock_instance

        # Patch verify method to fail
        with patch.object(KalshiClient, "_ensure_authenticated", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = False

            client = KalshiClient()
            result = await client.get_markets()

            # Should return empty list and NOT call API
            assert result == []
            mock_instance.get.assert_not_called()

# --- BUG #3: Zero Price Treated as Invalid ---

@pytest.mark.asyncio
async def test_bug_3_zero_price_is_treated_as_valid():
    """
    Verify that a market price of 0.0 is treated as a valid price and not ignored.
    Bug caused 0.0 to be treated as falsy and replaced with default (-1.0).
    """
    config = EngineConfig(
        mode=TradingMode.SIMULATION,
        enable_alpha_one=False,
        enable_alpha_two=False,
        enable_websocket=False,
        polymarket_key="test_key"
    )
    engine = UnifiedTradingEngine(config)

    # Mock PolymarketClient
    mock_poly = AsyncMock()
    engine.polymarket = mock_poly

    # Mock fixture
    mock_fixture = MagicMock()
    mock_fixture.home_team = "Home"
    mock_fixture.away_team = "Away"
    mock_fixture.fixture_id = 123

    # Mock get_markets_by_event
    mock_market = {
        "clobTokenIds": ["token123"]
    }
    mock_poly.get_markets_by_event.return_value = [mock_market]

    # Mock get_yes_price returning 0.0
    mock_poly.get_yes_price.return_value = 0.0

    # Act
    prices = await engine._get_fixture_market_prices(mock_fixture)

    # Assert
    assert prices[KEY_YES] == 0.0
    assert prices[KEY_NO] == 1.0

# --- BUG #4: CLI Flags ---

def test_bug_4_cli_flags_respect_env_vars_when_omitted():
    """
    Verify that omitting CLI flags respects environment variables (default behavior),
    and that specific flags correctly override them.
    Bug claimed flags were always True due to bad default.
    """
    # Case 1: Env says FALSE, CLI omitted -> Config is FALSE
    with patch.dict(os.environ, {"ENABLE_ALPHA_ONE": "false"}):
        args = parse_cli_args([])
        config = build_engine_config_from_cli_args(args)
        assert config.enable_alpha_one is False

    # Case 2: Env says TRUE, CLI omitted -> Config is TRUE
    with patch.dict(os.environ, {"ENABLE_ALPHA_ONE": "true"}):
        args = parse_cli_args([])
        config = build_engine_config_from_cli_args(args)
        assert config.enable_alpha_one is True

    # Case 3: Env says FALSE, CLI --alpha-one -> Config is TRUE (Override)
    with patch.dict(os.environ, {"ENABLE_ALPHA_ONE": "false"}):
        args = parse_cli_args(["--alpha-one"])
        config = build_engine_config_from_cli_args(args)
        assert config.enable_alpha_one is True

    # Case 4: Env says TRUE, CLI --no-alpha-one -> Config is FALSE (Override)
    with patch.dict(os.environ, {"ENABLE_ALPHA_ONE": "true"}):
        args = parse_cli_args(["--no-alpha-one"])
        config = build_engine_config_from_cli_args(args)
        assert config.enable_alpha_one is False

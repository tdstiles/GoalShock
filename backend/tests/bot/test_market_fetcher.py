import os
import sys
from datetime import datetime, timezone
from typing import List

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(PROJECT_ROOT)

from backend.bot.market_fetcher import MarketFetcher
from backend.models.schemas import MarketPrice, MarketUpdate


@pytest.fixture
def market_fetcher() -> MarketFetcher:
    """Create a MarketFetcher instance for testing.

    Returns:
        MarketFetcher: The market fetcher under test.
    """
    return MarketFetcher()


def _make_market_price(
    market_id: str,
    yes_price: float,
    no_price: float,
    last_updated: datetime,
) -> MarketPrice:
    """Build a MarketPrice for test setup.

    Args:
        market_id: Identifier for the market.
        yes_price: The yes price for the market.
        no_price: The no price for the market.
        last_updated: Timestamp for last update.

    Returns:
        MarketPrice: The constructed market price.
    """
    return MarketPrice(
        market_id=market_id,
        fixture_id=1,
        question="Will Team A win?",
        yes_price=yes_price,
        no_price=no_price,
        source="polymarket",
        last_updated=last_updated,
        home_team="Team A",
        away_team="Team B",
    )


@pytest.mark.asyncio
async def test_process_polymarket_non_matching_type_no_update(
    market_fetcher: MarketFetcher,
) -> None:
    """Ignore polymarket messages with non-matching types.

    Args:
        market_fetcher: The market fetcher under test.
    """
    callbacks: List[MarketUpdate] = []

    async def async_callback(update: MarketUpdate) -> None:
        """Capture async market updates.

        Args:
            update: Incoming market update.
        """
        callbacks.append(update)

    def sync_callback(update: MarketUpdate) -> None:
        """Capture sync market updates.

        Args:
            update: Incoming market update.
        """
        callbacks.append(update)

    market_fetcher.register_update_callback(async_callback)
    market_fetcher.register_update_callback(sync_callback)

    last_updated = datetime(2020, 1, 1, tzinfo=timezone.utc)
    market_fetcher.market_cache["mkt-1"] = _make_market_price(
        "mkt-1",
        yes_price=0.4,
        no_price=0.6,
        last_updated=last_updated,
    )

    await market_fetcher._process_polymarket_update(
        {"type": "other_message", "market_id": "mkt-1"}
    )

    cached = market_fetcher.market_cache["mkt-1"]
    assert cached.yes_price == 0.4
    assert cached.no_price == 0.6
    assert cached.last_updated == last_updated
    assert callbacks == []


@pytest.mark.asyncio
async def test_process_polymarket_update_with_cache_updates_and_callbacks(
    market_fetcher: MarketFetcher,
) -> None:
    """Update polymarket cache and notify callbacks for valid updates.

    Args:
        market_fetcher: The market fetcher under test.
    """
    async_updates: List[MarketUpdate] = []
    sync_updates: List[MarketUpdate] = []

    async def async_callback(update: MarketUpdate) -> None:
        """Capture async market updates.

        Args:
            update: Incoming market update.
        """
        async_updates.append(update)

    def sync_callback(update: MarketUpdate) -> None:
        """Capture sync market updates.

        Args:
            update: Incoming market update.
        """
        sync_updates.append(update)

    market_fetcher.register_update_callback(async_callback)
    market_fetcher.register_update_callback(sync_callback)

    last_updated = datetime(2020, 1, 1, tzinfo=timezone.utc)
    market_fetcher.market_cache["mkt-2"] = _make_market_price(
        "mkt-2",
        yes_price=0.3,
        no_price=0.7,
        last_updated=last_updated,
    )

    await market_fetcher._process_polymarket_update(
        {
            "type": "price_update",
            "market_id": "mkt-2",
            "yes_price": 0.55,
            "no_price": 0.45,
        }
    )

    cached = market_fetcher.market_cache["mkt-2"]
    assert cached.yes_price == 0.55
    assert cached.no_price == 0.45
    assert cached.last_updated != last_updated
    assert len(async_updates) == 1
    assert len(sync_updates) == 1
    assert async_updates[0].market_id == "mkt-2"
    assert async_updates[0].yes_price == 0.55
    assert async_updates[0].no_price == 0.45


@pytest.mark.asyncio
async def test_process_kalshi_non_matching_type_no_update(
    market_fetcher: MarketFetcher,
) -> None:
    """Ignore kalshi messages with non-matching types.

    Args:
        market_fetcher: The market fetcher under test.
    """
    callbacks: List[MarketUpdate] = []

    async def async_callback(update: MarketUpdate) -> None:
        """Capture async market updates.

        Args:
            update: Incoming market update.
        """
        callbacks.append(update)

    def sync_callback(update: MarketUpdate) -> None:
        """Capture sync market updates.

        Args:
            update: Incoming market update.
        """
        callbacks.append(update)

    market_fetcher.register_update_callback(async_callback)
    market_fetcher.register_update_callback(sync_callback)

    last_updated = datetime(2020, 1, 1, tzinfo=timezone.utc)
    market_fetcher.market_cache["mkt-3"] = _make_market_price(
        "mkt-3",
        yes_price=0.41,
        no_price=0.59,
        last_updated=last_updated,
    )

    await market_fetcher._process_kalshi_update(
        {"type": "unknown", "market_ticker": "mkt-3"}
    )

    cached = market_fetcher.market_cache["mkt-3"]
    assert cached.yes_price == 0.41
    assert cached.no_price == 0.59
    assert cached.last_updated == last_updated
    assert callbacks == []


@pytest.mark.asyncio
async def test_process_kalshi_update_normalizes_prices_and_callbacks(
    market_fetcher: MarketFetcher,
) -> None:
    """Normalize kalshi prices and notify callbacks for updates.

    Args:
        market_fetcher: The market fetcher under test.
    """
    async_updates: List[MarketUpdate] = []
    sync_updates: List[MarketUpdate] = []

    async def async_callback(update: MarketUpdate) -> None:
        """Capture async market updates.

        Args:
            update: Incoming market update.
        """
        async_updates.append(update)

    def sync_callback(update: MarketUpdate) -> None:
        """Capture sync market updates.

        Args:
            update: Incoming market update.
        """
        sync_updates.append(update)

    market_fetcher.register_update_callback(async_callback)
    market_fetcher.register_update_callback(sync_callback)

    last_updated = datetime(2020, 1, 1, tzinfo=timezone.utc)
    market_fetcher.market_cache["mkt-4"] = _make_market_price(
        "mkt-4",
        yes_price=0.25,
        no_price=0.75,
        last_updated=last_updated,
    )

    await market_fetcher._process_kalshi_update(
        {
            "type": "market_snapshot",
            "market_ticker": "mkt-4",
            "yes_bid": 55.0,
            "no_ask": 45.0,
        }
    )

    cached = market_fetcher.market_cache["mkt-4"]
    assert cached.yes_price == 0.55
    assert cached.no_price == 0.45
    assert cached.last_updated != last_updated
    assert len(async_updates) == 1
    assert len(sync_updates) == 1
    assert async_updates[0].yes_price == 0.55
    assert async_updates[0].no_price == 0.45


@pytest.mark.asyncio
async def test_apply_market_update_updates_cache_and_notifies(
    market_fetcher: MarketFetcher,
) -> None:
    """Update cache entries and notify callbacks through the helper.

    Args:
        market_fetcher: The market fetcher under test.
    """
    updates: List[MarketUpdate] = []

    def sync_callback(update: MarketUpdate) -> None:
        """Capture sync updates for assertions.

        Args:
            update: Incoming market update.
        """
        updates.append(update)

    market_fetcher.register_update_callback(sync_callback)

    last_updated = datetime(2021, 1, 1, tzinfo=timezone.utc)
    market_fetcher.market_cache["mkt-5"] = _make_market_price(
        "mkt-5",
        yes_price=0.2,
        no_price=0.8,
        last_updated=last_updated,
    )

    await market_fetcher._apply_market_update("mkt-5", yes_price=0.62, no_price=0.38)

    cached = market_fetcher.market_cache["mkt-5"]
    assert cached.yes_price == 0.62
    assert cached.no_price == 0.38
    assert cached.last_updated != last_updated
    assert len(updates) == 1
    assert updates[0].market_id == "mkt-5"
    assert updates[0].yes_price == 0.62
    assert updates[0].no_price == 0.38

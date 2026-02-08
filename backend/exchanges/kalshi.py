import os
import httpx
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class KalshiClient:
    """Client for interacting with Kalshi trading APIs."""

    def __init__(self) -> None:
        """Initialize the Kalshi client and credentials.

        Credentials are sourced from environment variables.
        """
        self.api_key = os.getenv("KALSHI_API_KEY", "")
        self.api_secret = os.getenv("KALSHI_API_SECRET", "")
        self.base_url = "https://trading-api.kalshi.com/trade-api/v2"
        self.client = httpx.AsyncClient(timeout=10.0)
        self.auth_token: Optional[str] = None

        logger.info("📊 Kalshi client initialized")

    async def login(self) -> bool:
        """Authenticate against Kalshi and store bearer token.

        Returns:
            bool: True when authentication succeeds and a token is stored.
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/login",
                json={"email": self.api_key, "password": self.api_secret},
            )

            if response.status_code == 200:
                token = response.json().get("token")
                if not token:
                    logger.error("❌ Kalshi auth succeeded but no token was returned")
                    self.auth_token = None
                    return False
                self.auth_token = token
                logger.info("✅ Kalshi authenticated successfully")
                return True

            logger.error("❌ Kalshi auth failed: %s", response.status_code)
            self.auth_token = None
            return False

        except Exception as exc:
            logger.error("Kalshi login error: %s", exc)
            self.auth_token = None
            return False

    # Fix: Bug #2 - Ensures authentication before API calls (Verified)
    async def _ensure_authenticated(self) -> bool:
        """Ensure an auth token is available before API requests.

        Returns:
            bool: True if authentication is available, otherwise False.
        """
        if self.auth_token:
            return True

        is_authenticated = await self.login()
        if not is_authenticated:
            logger.error("Kalshi authentication unavailable; request aborted")
            return False

        return bool(self.auth_token)

    async def get_markets(
        self, event_ticker: Optional[str] = None, status: str = "active"
    ) -> List[Dict]:
        """Fetch available markets.

        Args:
            event_ticker: Optional event ticker to filter by.
            status: Market status filter.

        Returns:
            List[Dict]: A list of market payloads.
        """
        if not await self._ensure_authenticated():
            logger.warning("Skipping Kalshi markets request because authentication failed")
            # Check auth for Bug #2 fix (Verified)
            return []

        try:
            params = {"status": status, "limit": 100}
            if event_ticker:
                params["event_ticker"] = event_ticker

            response = await self.client.get(
                f"{self.base_url}/markets",
                params=params,
                headers={"Authorization": f"Bearer {self.auth_token}"},
            )

            if response.status_code != 200:
                logger.error("Kalshi markets API error: %s", response.status_code)
                return []

            markets = response.json().get("markets", [])
            logger.info("Found %s Kalshi markets", len(markets))

            return markets

        except Exception as exc:
            logger.error("Error fetching Kalshi markets: %s", exc)
            return []

    async def get_orderbook(self, ticker: str) -> Optional[Dict]:
        """Fetch and normalize orderbook data for a market ticker.

        Args:
            ticker: Kalshi market ticker.

        Returns:
            Optional[Dict]: Normalized orderbook snapshot, else None.
        """
        if not await self._ensure_authenticated():
            logger.warning(
                "Skipping Kalshi orderbook request for %s because authentication failed",
                ticker,
            )
            return None

        try:
            response = await self.client.get(
                f"{self.base_url}/markets/{ticker}/orderbook",
                headers={"Authorization": f"Bearer {self.auth_token}"},
            )

            if response.status_code != 200:
                logger.error("Orderbook API error: %s", response.status_code)
                return None

            data = response.json()
            orderbook = data.get("orderbook", {})

            yes_bids = orderbook.get("yes", [])
            no_bids = orderbook.get("no", [])

            if not yes_bids:
                logger.warning("Empty orderbook for %s", ticker)
                return None

            yes_bid = yes_bids[0][0] if yes_bids else 0
            yes_ask = (100 - no_bids[0][0]) if no_bids else 100

            yes_bid_decimal = yes_bid / 100
            yes_ask_decimal = yes_ask / 100
            mid_price = (yes_bid_decimal + yes_ask_decimal) / 2

            logger.debug("Orderbook for %s:", ticker)
            logger.debug("  YES Bid: %s¢ (%.2f)", yes_bid, yes_bid_decimal)
            logger.debug("  YES Ask: %s¢ (%.2f)", yes_ask, yes_ask_decimal)
            logger.debug("  Mid: %.4f (%.1f%%)", mid_price, mid_price * 100)

            return {
                "ticker": ticker,
                "yes_bid": yes_bid_decimal,
                "yes_ask": yes_ask_decimal,
                "mid_price": mid_price,
                "spread": yes_ask_decimal - yes_bid_decimal,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as exc:
            logger.error("Error fetching orderbook: %s", exc)
            return None

    async def get_yes_price(self, ticker: str) -> Optional[float]:
        """Get the best ask YES probability for a market.

        Args:
            ticker: Kalshi market ticker.

        Returns:
            Optional[float]: Decimal yes ask price or None when unavailable.
        """
        orderbook = await self.get_orderbook(ticker)

        if not orderbook:
            return None

        yes_price = orderbook["yes_ask"]

        logger.info("YES price for %s: %.4f (%.1f%%)", ticker, yes_price, yes_price * 100)

        return yes_price

    async def place_order(
        self,
        ticker: str,
        side: str,
        action: str,
        count: int,
        price: int,
    ) -> Optional[Dict]:
        """Place a limit order on Kalshi.

        Args:
            ticker: Kalshi market ticker.
            side: Contract side (yes/no).
            action: Trade direction (buy/sell).
            count: Number of contracts.
            price: Price in cents.

        Returns:
            Optional[Dict]: Order payload when placed successfully.
        """
        if not await self._ensure_authenticated():
            logger.warning(
                "Skipping Kalshi order placement for %s because authentication failed",
                ticker,
            )
            return None

        try:
            normalized_side = side.lower()
            order_payload = {
                "ticker": ticker,
                "side": normalized_side,
                "action": action.lower(),
                "count": count,
                "type": "limit",
                "yes_price": price if normalized_side == "yes" else None,
                "no_price": price if normalized_side == "no" else None,
            }

            response = await self.client.post(
                f"{self.base_url}/portfolio/orders",
                json=order_payload,
                headers={"Authorization": f"Bearer {self.auth_token}"},
            )

            if response.status_code == 200:
                order = response.json().get("order", {})
                order_id = order.get("order_id")
                logger.info("✅ Kalshi order placed: %s", order_id)
                return order

            logger.error("❌ Kalshi order failed: %s", response.text)
            return None

        except Exception as exc:
            logger.error("Error placing Kalshi order: %s", exc)
            return None

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()

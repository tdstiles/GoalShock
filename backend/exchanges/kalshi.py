"""
Kalshi API Integration
Direct orderbook access - NO probability calculations
"""
import os
import asyncio
import httpx
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class KalshiClient:
    """
    Kalshi Exchange API client

    Prices are CENTS (0-100 scale):
    - YES @ 42 cents = 42% probability
    - NO @ 58 cents = 58% probability

    We convert cents to decimal (42 → 0.42) but NO implied probability math
    """

    def __init__(self):
        self.api_key = os.getenv("KALSHI_API_KEY", "")  # Email
        self.api_secret = os.getenv("KALSHI_API_SECRET", "")  # Password
        self.base_url = "https://trading-api.kalshi.com/trade-api/v2"
        self.client = httpx.AsyncClient(timeout=10.0)
        self.auth_token = None

        logger.info("📊 Kalshi client initialized")

    async def login(self) -> bool:
        """Authenticate with Kalshi and get session token"""
        try:
            response = await self.client.post(
                f"{self.base_url}/login",
                json={"email": self.api_key, "password": self.api_secret}
            )

            if response.status_code == 200:
                self.auth_token = response.json().get("token")
                logger.info("✅ Kalshi authenticated successfully")
                return True
            else:
                logger.error(f"❌ Kalshi auth failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Kalshi login error: {e}")
            return False

    async def get_markets(self, event_ticker: str = None, status: str = "active") -> List[Dict]:
        """
        Get markets from Kalshi

        Args:
            event_ticker: Filter by event (e.g., "SOCCER-MANCITY-2024")
            status: "active", "settled", or "all"

        Returns list of markets with YES/NO prices
        """
        if not self.auth_token:
            await self.login()

        try:
            params = {"status": status, "limit": 100}
            if event_ticker:
                params["event_ticker"] = event_ticker

            response = await self.client.get(
                f"{self.base_url}/markets",
                params=params,
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )

            if response.status_code != 200:
                logger.error(f"Kalshi markets API error: {response.status_code}")
                return []

            markets = response.json().get("markets", [])
            logger.info(f"Found {len(markets)} Kalshi markets")

            return markets

        except Exception as e:
            logger.error(f"Error fetching Kalshi markets: {e}")
            return []

    async def get_orderbook(self, ticker: str) -> Optional[Dict]:
        """
        Get orderbook for a specific market

        Returns:
        {
            "ticker": "SOCCER-MANCITY-YES",
            "yes_bid": 42,  # 42 cents = 42%
            "yes_ask": 44,  # 44 cents = 44%
            "no_bid": 56,
            "no_ask": 58
        }

        CRITICAL: Cents are RAW probabilities (42 cents = 0.42 = 42%)
        """
        if not self.auth_token:
            await self.login()

        try:
            response = await self.client.get(
                f"{self.base_url}/markets/{ticker}/orderbook",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )

            if response.status_code != 200:
                logger.error(f"Orderbook API error: {response.status_code}")
                return None

            data = response.json()
            orderbook = data.get("orderbook", {})

            yes_bids = orderbook.get("yes", [])
            no_bids = orderbook.get("no", [])

            if not yes_bids:
                logger.warning(f"Empty orderbook for {ticker}")
                return None

            # Extract best prices (in cents)
            yes_bid = yes_bids[0][0] if yes_bids else 0  # Best YES buy price
            yes_ask = no_bids[0][0] if no_bids else 100  # Best YES sell price (inverse of NO bid)

            # Convert cents to decimal (42 → 0.42)
            yes_bid_decimal = yes_bid / 100
            yes_ask_decimal = yes_ask / 100
            mid_price = (yes_bid_decimal + yes_ask_decimal) / 2

            logger.debug(f"Orderbook for {ticker}:")
            logger.debug(f"  YES Bid: {yes_bid}¢ ({yes_bid_decimal:.2f})")
            logger.debug(f"  YES Ask: {yes_ask}¢ ({yes_ask_decimal:.2f})")
            logger.debug(f"  Mid: {mid_price:.4f} ({mid_price*100:.1f}%)")

            return {
                "ticker": ticker,
                "yes_bid": yes_bid_decimal,
                "yes_ask": yes_ask_decimal,
                "mid_price": mid_price,
                "spread": yes_ask_decimal - yes_bid_decimal,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return None

    async def get_yes_price(self, ticker: str) -> Optional[float]:
        """
        Get current YES price (to buy outcome)

        Returns raw probability (e.g., 0.42 = 42%)
        NO IMPLIED PROBABILITY CALCULATION - DIRECT CONVERSION FROM CENTS
        """
        orderbook = await self.get_orderbook(ticker)

        if not orderbook:
            return None

        # Return best ask (price to buy YES) in decimal
        yes_price = orderbook["yes_ask"]

        logger.info(f"YES price for {ticker}: {yes_price:.4f} ({yes_price*100:.1f}%)")

        return yes_price

    async def place_order(
        self,
        ticker: str,
        side: str,  # 'yes' or 'no'
        action: str,  # 'buy' or 'sell'
        count: int,  # Number of contracts
        price: int  # Price in cents (e.g., 42 for 42%)
    ) -> Optional[Dict]:
        """
        Place limit order on Kalshi

        Args:
            ticker: Market ticker
            side: 'yes' or 'no'
            action: 'buy' or 'sell'
            count: Number of contracts
            price: Limit price in CENTS (0-100)

        Returns order confirmation or None if failed
        """
        if not self.auth_token:
            await self.login()

        try:
            order_payload = {
                "ticker": ticker,
                "side": side.lower(),
                "action": action.lower(),
                "count": count,
                "type": "limit",
                "yes_price": price if side == "yes" else None,
                "no_price": price if side == "no" else None
            }

            response = await self.client.post(
                f"{self.base_url}/portfolio/orders",
                json=order_payload,
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )

            if response.status_code == 200:
                order = response.json().get("order", {})
                order_id = order.get("order_id")
                logger.info(f"✅ Kalshi order placed: {order_id}")
                return order
            else:
                logger.error(f"❌ Kalshi order failed: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error placing Kalshi order: {e}")
            return None

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

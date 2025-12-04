"""
Polymarket API Integration
Direct orderbook access - NO probability calculations
"""
import os
import asyncio
import httpx
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PolymarketClient:
    """
    Polymarket CLOB (Central Limit Order Book) client

    Prices are ALREADY probabilities:
    - YES price of 0.42 = 42% probability
    - NO price of 0.58 = 58% probability
    """

    def __init__(self):
        self.api_key = os.getenv("POLYMARKET_API_KEY", "")
        self.base_url = "https://clob.polymarket.com"
        self.gamma_url = "https://gamma-api.polymarket.com"
        self.client = httpx.AsyncClient(timeout=10.0)

        logger.info("📊 Polymarket client initialized")

    async def get_markets_by_event(self, event_name: str) -> List[Dict]:
        """
        Search for markets by event name (e.g., "Manchester City vs Liverpool")

        Returns list of markets with YES/NO prices
        """
        try:
            response = await self.client.get(
                f"{self.gamma_url}/markets",
                params={"search": event_name, "active": True}
            )

            if response.status_code != 200:
                logger.error(f"Polymarket API error: {response.status_code}")
                return []

            markets = response.json()
            logger.info(f"Found {len(markets)} markets for: {event_name}")

            return markets

        except Exception as e:
            logger.error(f"Error fetching Polymarket markets: {e}")
            return []

    async def get_orderbook(self, token_id: str) -> Optional[Dict]:
        """
        Get orderbook for a specific market token

        Returns:
        {
            "market": "Man City to win",
            "asset_id": "0x123...",
            "bids": [
                {"price": "0.42", "size": "1500.50"},  # YES @ 42%
                {"price": "0.41", "size": "2000.00"}
            ],
            "asks": [
                {"price": "0.43", "size": "1200.00"},
                {"price": "0.44", "size": "800.00"}
            ]
        }

        CRITICAL: Prices are RAW probabilities - NO CONVERSION NEEDED
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/book",
                params={"token_id": token_id}
            )

            if response.status_code != 200:
                logger.error(f"Orderbook API error: {response.status_code}")
                return None

            orderbook = response.json()

            # Extract best bid/ask (top of book)
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            if not bids or not asks:
                logger.warning(f"Empty orderbook for token {token_id}")
                return None

            best_bid = float(bids[0]["price"])  # Highest YES buy price
            best_ask = float(asks[0]["price"])  # Lowest YES sell price
            mid_price = (best_bid + best_ask) / 2

            logger.debug(f"Orderbook for {token_id}:")
            logger.debug(f"  Best Bid: {best_bid:.4f} ({best_bid*100:.2f}%)")
            logger.debug(f"  Best Ask: {best_ask:.4f} ({best_ask*100:.2f}%)")
            logger.debug(f"  Mid: {mid_price:.4f} ({mid_price*100:.2f}%)")

            return {
                "token_id": token_id,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "mid_price": mid_price,
                "spread": best_ask - best_bid,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return None

    async def get_yes_price(self, token_id: str) -> Optional[float]:
        """
        Get current YES price (to buy outcome)

        Returns raw probability (e.g., 0.35 = 35%)
        NO IMPLIED PROBABILITY CALCULATION - THIS IS THE PROBABILITY
        """
        orderbook = await self.get_orderbook(token_id)

        if not orderbook:
            return None

        # Return best ask (price to buy YES)
        yes_price = orderbook["best_ask"]

        logger.info(f"YES price for {token_id}: {yes_price:.4f} ({yes_price*100:.1f}%)")

        return yes_price

    async def place_order(
        self,
        token_id: str,
        side: str,  # 'BUY' or 'SELL'
        price: float,
        size: float
    ) -> Optional[Dict]:
        """
        Place limit order on Polymarket

        Args:
            token_id: Market token ID
            side: 'BUY' or 'SELL'
            price: Limit price (e.g., 0.42 for 42%)
            size: Order size in USD

        Returns order confirmation or None if failed
        """
        try:
            # Polymarket requires signed orders
            # In production: Use private key to sign order
            order_payload = {
                "token_id": token_id,
                "side": side.upper(),
                "price": str(price),
                "size": str(size),
                "timestamp": int(datetime.now().timestamp())
            }

            # TODO: Sign order with private key
            # signature = sign_order(order_payload, private_key)

            response = await self.client.post(
                f"{self.base_url}/order",
                json=order_payload,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )

            if response.status_code == 200:
                order_id = response.json().get("order_id")
                logger.info(f"✅ Order placed: {order_id}")
                return response.json()
            else:
                logger.error(f"❌ Order failed: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

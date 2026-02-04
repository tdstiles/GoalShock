
import os
import asyncio
import httpx
import logging
from typing import Dict, Optional, List
from datetime import datetime
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class PolymarketClient:
   

    def __init__(self):
        self.api_key = os.getenv("POLYMARKET_API_KEY", "")
        self.base_url = "https://clob.polymarket.com"
        self.gamma_url = "https://gamma-api.polymarket.com"
        self.client = httpx.AsyncClient(timeout=10.0)

        # Initialize authenticated ClobClient if private key is present
        self.clob_client = None
        self.private_key = settings.POLYMARKET_PRIVATE_KEY

        if self.private_key:
            try:
                # ClobClient handles EIP-712 signing
                self.clob_client = ClobClient(
                    host=self.base_url,
                    key=self.private_key,
                    chain_id=settings.POLYMARKET_CHAIN_ID
                )
                logger.info("🔐 ClobClient initialized with private key")
            except Exception as e:
                logger.error(f"Failed to initialize ClobClient: {e}")

        logger.info("📊 Polymarket client initialized")

    async def get_markets_by_event(self, event_name: str) -> List[Dict]:
        
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

    async def get_market(self, market_id: str) -> Optional[Dict]:
        """
        Fetches market details from Gamma API by ID.
        """
        try:
            response = await self.client.get(
                f"{self.gamma_url}/markets/{market_id}"
            )

            if response.status_code != 200:
                logger.error(f"Polymarket API error (get_market): {response.status_code}")
                return None

            return response.json()

        except Exception as e:
            logger.error(f"Error fetching Polymarket market {market_id}: {e}")
            return None

    async def get_orderbook(self, token_id: str) -> Optional[Dict]:
       
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

            best_bid = float(bids[0]["price"])  
            best_ask = float(asks[0]["price"]) 
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
      
        orderbook = await self.get_orderbook(token_id)

        if not orderbook:
            return None

      
        yes_price = orderbook["best_ask"]

        logger.info(f"YES price for {token_id}: {yes_price:.4f} ({yes_price*100:.1f}%)")

        return yes_price

    async def get_bid_price(self, token_id: str) -> Optional[float]:
        """
        Returns the Best Bid price (Sell Price) for a given token.
        """
        orderbook = await self.get_orderbook(token_id)

        if not orderbook:
            return None

        bid_price = orderbook["best_bid"]

        logger.info(f"BID price for {token_id}: {bid_price:.4f} ({bid_price*100:.1f}%)")

        return bid_price

    async def place_order(
        self,
        token_id: str,
        side: str,  
        price: float,
        size: float
    ) -> Optional[Dict]:
       
        try:
            if not self.clob_client:
                logger.error("❌ Cannot place order: Private Key missing (ClobClient not initialized)")
                return None

            # Create OrderArgs (py-clob-client handles signing)
            order_args = OrderArgs(
                price=price,
                size=size,
                side=side.upper(),
                token_id=token_id
            )

            # Execute in thread to avoid blocking event loop if client is sync
            response = await asyncio.to_thread(
                self.clob_client.create_and_post_order,
                order_args
            )

            if response and response.get("orderID"):
                order_id = response.get("orderID")
                logger.info(f"✅ Signed Order placed: {order_id}")
                # Ensure backward compatibility
                if isinstance(response, dict):
                    response["order_id"] = order_id
                return response
            else:
                logger.error(f"❌ Order placement returned unexpected response: {response}")
                return response

        except Exception as e:
            logger.error(f"Error placing signed order: {e}")
            return None

    async def get_order(self, order_id: str) -> Optional[Dict]:
        """
        Fetches order details by ID.
        """
        try:
            if not self.clob_client:
                return None

            # clob_client.get_order returns the order dict directly
            return await asyncio.to_thread(self.clob_client.get_order, order_id)
        except Exception as e:
            logger.error(f"Error fetching order {order_id}: {e}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancels an order by ID.
        """
        try:
            if not self.clob_client:
                return False

            await asyncio.to_thread(self.clob_client.cancel, order_id)
            logger.info(f"🚫 Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    async def place_order_and_wait_for_fill(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        timeout: int = 5,
        poll_interval: float = 1.0
    ) -> Optional[Dict]:
        """
        Places an order and polls for fill confirmation.
        Returns the order dict if filled/matched, None otherwise (cancels on timeout).
        """
        # Place the order
        order_res = await self.place_order(token_id, side, price, size)

        # Check if placement failed
        if not order_res:
            return None

        order_id = order_res.get("orderID") or order_res.get("order_id")
        if not order_id:
             logger.error(f"Order placement returned no ID: {order_res}")
             return None

        logger.info(f"Order placed ({order_id}). Verifying fill...")

        # Poll loop
        steps = int(timeout / poll_interval)
        if steps < 1:
            steps = 1

        for i in range(steps):
            await asyncio.sleep(poll_interval)
            order_status = await self.get_order(order_id)

            if not order_status:
                continue

            status = str(order_status.get("status") or order_status.get("state") or "").upper()

            if status in ["MATCHED", "FILLED"]:
                logger.info(f"Order {order_id} filled.")
                return order_status

            if status in ["CANCELED", "CANCELLED", "KILLED"]:
                logger.warning(f"Order {order_id} was canceled during verification.")
                return None

        # Timeout
        logger.warning(f"Order {order_id} not filled after {timeout}s. Cancelling...")
        await self.cancel_order(order_id)
        return None

    async def close(self):
        await self.client.aclose()

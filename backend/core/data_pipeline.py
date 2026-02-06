
import os
import time
import httpx
import random
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# --- CONFIGURATION CONSTANTS ---
API_KEY_MIN_LENGTH = 20

# --- SYNTHETIC DATA CONSTANTS ---
SYNTH_TEAMS = [
    ("Manchester City", "Liverpool"),
    ("Real Madrid", "Barcelona"),
    ("Bayern Munich", "Borussia Dortmund"),
    ("PSG", "Marseille"),
    ("Arsenal", "Chelsea")
]

SYNTH_PLAYERS = [
    "Haaland", "Salah", "Mbappe", "Lewandowski", "Kane",
    "Vinicius Jr", "Saka", "De Bruyne", "Rodri", "Bellingham"
]

SYNTH_MATCHES_MIN = 2
SYNTH_MATCHES_MAX = 4
SYNTH_GOALS_MIN = 1
SYNTH_GOALS_MAX = 3
SYNTH_MATCH_DURATION_MIN = 1
SYNTH_MATCH_DURATION_MAX = 90
SYNTH_TIME_OFFSET_MAX = 45


class GoalEvent:
    """Represents a single goal event emitted by a live or synthetic feed."""

    def __init__(self, match_id: str, team: str, player: str, minute: int, timestamp: datetime):
        """Initialize a goal event.

        Args:
            match_id: Provider fixture ID or synthetic fixture identifier.
            team: Team name credited with the goal.
            player: Player name credited with the goal.
            minute: Match minute when the goal occurred.
            timestamp: Event timestamp in UTC/local runtime clock.
        """
        self.match_id = match_id
        self.team = team
        self.player = player
        self.minute = minute
        self.timestamp = timestamp


class PrimaryProviderUnavailableError(RuntimeError):
    """Raised when a primary-mode provider call fails and synthetic fallback is disallowed."""

    def __init__(self, operation: str, source: str, status_code: Optional[int], message: str):
        """Initialize primary provider failure metadata.

        Args:
            operation: Logical operation that failed (for example, ``fetch_live_goals``).
            source: Upstream provider/source name.
            status_code: HTTP status code when available.
            message: Human-readable error message.
        """
        self.operation = operation
        self.source = source
        self.status_code = status_code
        self.message = message
        super().__init__(
            f"Primary provider unavailable during {operation} via {source}"
            f" (status={status_code}): {message}"
        )

class DataAcquisitionLayer:
    """Acquires live goal and market data from providers or synthetic generators."""

    def __init__(self):
        """Create a data acquisition layer and initialize provider credentials."""
        self._api_football_key = os.getenv("API_FOOTBALL_KEY", "")
        self._polymarket_key = os.getenv("POLYMARKET_API_KEY", "")
        self._kalshi_key = os.getenv("KALSHI_API_KEY", "")
        self._kalshi_secret = os.getenv("KALSHI_API_SECRET", "")

        self._srvc_mode = self._determine_operational_mode()
        self._client = httpx.AsyncClient(timeout=10.0)

    def _determine_operational_mode(self) -> str:
        """Determine whether runtime should use primary or auxiliary mode.

        Returns:
            ``"primary"`` when required credentials are configured; otherwise ``"auxiliary"``.
        """
        if self._api_football_key and len(self._api_football_key) > API_KEY_MIN_LENGTH:
            if self._polymarket_key or (self._kalshi_key and self._kalshi_secret):
                return "primary"
        return "auxiliary"

    async def fetch_live_goals(self) -> List[GoalEvent]:
        """Fetch live goals with explicit primary-mode failure semantics.

        Returns:
            Goal events from provider in primary mode, or synthetic events in auxiliary mode.

        Raises:
            PrimaryProviderUnavailableError: If the primary provider fails in primary mode.
        """
        if self._srvc_mode == "primary":
            try:
                return await self._fetch_verified_goals()
            except Exception as e:
                logger.error(
                    "Primary provider unavailable for live goals; synthetic fallback blocked in primary mode.",
                    extra={"source": "api_football", "mode": self._srvc_mode},
                    exc_info=True,
                )
                raise PrimaryProviderUnavailableError(
                    operation="fetch_live_goals",
                    source="api_football",
                    status_code=getattr(getattr(e, "response", None), "status_code", None),
                    message=str(e),
                ) from e
        logger.info("Using synthetic goal stream by design (auxiliary mode).")
        return await self._generate_event_stream()

    async def _fetch_verified_goals(self) -> List[GoalEvent]:
        start_time = time.time()
        # Use new Direct API headers
        headers = {
            "x-apisports-key": self._api_football_key
        }

        try:
            # Use new Direct API URL
            response = await self._client.get(
                "https://v3.football.api-sports.io/fixtures",
                headers=headers,
                params={"live": "all"}
            )

            duration = time.time() - start_time
            if duration > 1.0:
                logger.warning(f"Slow API response from API-Football: {duration:.3f}s")

            if response.status_code != 200:
                logger.error(f"API-Football error {response.status_code}: {response.text[:200]}")
                raise Exception(f"API request failed with status {response.status_code}")

            data = response.json()
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"API-Football request failed after {duration:.3f}s: {e}")
            raise
        goals = []

        for fixture in data.get("response", []):
            events = fixture.get("events", [])
            for event in events:
                if event.get("type") == "Goal":
                    goals.append(GoalEvent(
                        match_id=str(fixture["fixture"]["id"]),
                        team=event["team"]["name"],
                        player=event["player"]["name"],
                        minute=event["time"]["elapsed"],
                        timestamp=datetime.now()
                    ))

        return goals

    async def _generate_event_stream(self) -> List[GoalEvent]:
        """Generate synthetic goal events for auxiliary/demo operation."""
        goals = []
        num_matches = random.randint(SYNTH_MATCHES_MIN, SYNTH_MATCHES_MAX)

        for i in range(num_matches):
            team_pair = random.choice(SYNTH_TEAMS)
            num_goals = random.randint(SYNTH_GOALS_MIN, SYNTH_GOALS_MAX)

            for _ in range(num_goals):
                team = random.choice(team_pair)
                player = random.choice(SYNTH_PLAYERS)
                minute = random.randint(SYNTH_MATCH_DURATION_MIN, SYNTH_MATCH_DURATION_MAX)

                goals.append(GoalEvent(
                    match_id=f"synth_{i}",
                    team=team,
                    player=player,
                    minute=minute,
                    timestamp=datetime.now() - timedelta(minutes=random.randint(0, SYNTH_TIME_OFFSET_MAX))
                ))

        return sorted(goals, key=lambda x: x.timestamp, reverse=True)

    async def fetch_market_data(self, market_type: str = "football") -> Dict:
        """Fetch market data with explicit primary-mode failure semantics.

        Args:
            market_type: Market domain label for synthetic generation.

        Returns:
            Provider market payload in primary mode or synthetic market payload in auxiliary mode.

        Raises:
            PrimaryProviderUnavailableError: If the configured primary provider fails.
        """
        if self._srvc_mode == "primary":
            try:
                if self._polymarket_key:
                    return await self._fetch_polymarket_data()
                elif self._kalshi_key:
                    return await self._fetch_kalshi_data()
            except Exception as e:
                source = "polymarket" if self._polymarket_key else "kalshi"
                logger.error(
                    "Primary provider unavailable for market data; synthetic fallback blocked in primary mode.",
                    extra={"source": source, "mode": self._srvc_mode, "market_type": market_type},
                    exc_info=True,
                )
                raise PrimaryProviderUnavailableError(
                    operation="fetch_market_data",
                    source=source,
                    status_code=getattr(getattr(e, "response", None), "status_code", None),
                    message=str(e),
                ) from e
        logger.info("Using synthetic market data by design (auxiliary mode).", extra={"market_type": market_type})
        return await self._generate_market_data(market_type)

    async def _fetch_polymarket_data(self) -> Dict:
        start_time = time.time()
        headers = {"Authorization": f"Bearer {self._polymarket_key}"}

        try:
            response = await self._client.get(
                "https://api.polymarket.com/markets",
                headers=headers,
                params={"tag": "sports"}
            )

            duration = time.time() - start_time
            if duration > 1.0:
                logger.warning(f"Slow API response from Polymarket: {duration:.3f}s")

            if response.status_code != 200:
                logger.error(f"Polymarket error {response.status_code}: {response.text[:200]}")
                raise Exception("Polymarket API failed")

            return response.json()
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Polymarket request failed after {duration:.3f}s: {e}")
            raise

    async def _fetch_kalshi_data(self) -> Dict:
        start_time = time.time()
        try:
            auth_response = await self._client.post(
                "https://api.kalshi.com/v1/login",
                json={"email": self._kalshi_key, "password": self._kalshi_secret}
            )

            if auth_response.status_code != 200:
                logger.error(f"Kalshi auth error {auth_response.status_code}: {auth_response.text[:200]}")
                raise Exception("Kalshi auth failed")

            token = auth_response.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}

            markets_response = await self._client.get(
                "https://api.kalshi.com/v1/markets",
                headers=headers,
                params={"category": "sports"}
            )

            duration = time.time() - start_time
            if duration > 1.0:
                logger.warning(f"Slow API response from Kalshi: {duration:.3f}s")

            return markets_response.json()
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Kalshi request failed after {duration:.3f}s: {e}")
            raise

    async def _generate_market_data(self, market_type: str) -> Dict:
        """Generate synthetic market data for auxiliary/demo operation.

        Args:
            market_type: Market domain label.

        Returns:
            Synthetic market payload compatible with stream processing.
        """
        from .market_synthesizer import MarketMicrostructure
        from .synthetic_data import SYNTHETIC_MARKET_SCENARIOS

        mm = MarketMicrostructure()
        markets = []

        for idx, scenario in enumerate(SYNTHETIC_MARKET_SCENARIOS):
            market_id = f"market_{idx}"
            orderbook = mm.synthesize_orderbook(market_id, scenario["yes_price"])

            markets.append({
                "id": market_id,
                "question": scenario["question"],
                "yes_price": orderbook["mid_price"],
                "no_price": 1 - orderbook["mid_price"],
                "volume": orderbook["total_volume"],
                "bids": orderbook["bids"][:3],
                "asks": orderbook["asks"][:3],
                "last_trade_time": datetime.now().isoformat()
            })

        return {"markets": markets, "count": len(markets)}

    async def close(self):
        """Close underlying HTTP client resources."""
        await self._client.aclose()

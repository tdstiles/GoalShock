
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Dict, List, Optional

from backend.config.settings import settings
from backend.data.api_football import APIFootballClient, LiveFixture

logger = logging.getLogger(__name__)

MAX_SEEN_GOALS = 1000
SEEN_GOALS_TRIM_TO = 500


@dataclass
class GoalEventWS:
    """Represents a goal event (kept name for compatibility)."""

    fixture_id: int
    league_id: int
    league_name: str
    home_team: str
    away_team: str
    team: str
    player: str
    minute: int
    home_score: int
    away_score: int
    goal_type: str
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "fixture_id": self.fixture_id,
            "league_id": self.league_id,
            "league_name": self.league_name,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "team": self.team,
            "player": self.player,
            "minute": self.minute,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "goal_type": self.goal_type,
            "timestamp": self.timestamp.isoformat()
        }


GoalCallback = Callable[[GoalEventWS], Optional[Awaitable[None]]]


class WebSocketGoalListener:
    """
    Refactored to use POLLING instead of WebSockets, adhering to the new API requirements.
    The class name is retained to minimize refactoring impact on dependent modules.
    """
  
    SUPPORTED_LEAGUES = set(settings.SUPPORTED_LEAGUES)
    
    def __init__(self, api_key: str = "") -> None:
        """Initialize the listener with an optional API key override.

        Args:
            api_key: Optional API key to pass to the API-Football client.
        """
        self.api_key = api_key
        self.running = False

        # Use the shared client which is now updated for v3.football.api-sports.io
        self.client = APIFootballClient(api_key=self.api_key)
        
        self.goal_callbacks: List[GoalCallback] = []
        self.fixture_callbacks: List[Callable[[List[LiveFixture]], Optional[Awaitable[None]]]] = []
        
        self.active_fixtures: Dict[int, LiveFixture] = {}
        
        # Polling interval from settings
        self.poll_interval = settings.POLL_INTERVAL_SECONDS
        
        logger.info("Goal Listener (Polling Mode) initialized")

    def register_goal_callback(self, callback: GoalCallback) -> None:
        self.goal_callbacks.append(callback)
        logger.info(f"Registered goal callback: {callback.__name__}")

    def register_fixture_callback(self, callback: Callable[[List[LiveFixture]], Optional[Awaitable[None]]]) -> None:
        self.fixture_callbacks.append(callback)
        logger.info(f"Registered fixture callback: {callback.__name__}")

    async def start(self) -> None:
        """Start the polling loop."""
        self.running = True
        logger.info(f"Starting Goal Listener Loop (Interval: {self.poll_interval}s)...")
        
        while self.running:
            try:
                await self._poll_cycle()
            except Exception as e:
                logger.error(f"Error in polling cycle: {e}")

            # Wait for next cycle or until stopped
            if self.running:
                await asyncio.sleep(self.poll_interval)
    
    async def stop(self) -> None:
        self.running = False
        await self.client.close()
        logger.info("Goal Listener stopped")

    async def _poll_cycle(self) -> None:
        """Fetch live fixtures and detect changes."""
        fixtures = await self.client.get_live_fixtures()

        current_fixture_ids = set()

        for fixture in fixtures:
            current_fixture_ids.add(fixture.fixture_id)
            # Update active fixture cache
            self.active_fixtures[fixture.fixture_id] = fixture
            
            # Check for goals
            await self._detect_goals_in_fixture(fixture)

        # Sherlock Fix: Remove stale fixtures that are no longer live
        # to prevent infinite memory growth of 'active_fixtures'
        stale_ids = [fid for fid in self.active_fixtures if fid not in current_fixture_ids]
        for fid in stale_ids:
            del self.active_fixtures[fid]

        # Notify listeners of full fixture update
        await self._notify_fixture_callbacks(fixtures)

    async def _detect_goals_in_fixture(self, fixture: LiveFixture) -> None:
        """Compare current fixture state with previous state to detect goals."""
        fixture_id = fixture.fixture_id

        # We rely on APIFootballClient's internal previous_scores logic partially,
        # but since we are re-implementing the loop here, we can also use our own tracking
        # or leverage the client. However, APIFootballClient.detect_goals returns a list of Goal objects.
        # Let's use that for consistency if we were just calling it once, but we need to track state persistently.

        # Actually, APIFootballClient maintains `previous_scores`.
        # But we instantiated a new `APIFootballClient` inside `__init__`.
        # So we can use `client.detect_goals([fixture])`.

        goals = await self.client.detect_goals([fixture])

        for goal in goals:
            # Create a unique ID for deduplication (handled by client too, but good to double check)
            # The client detects changes, so 'goals' are strictly NEW changes.
            
            # Construct the event object expected by consumers
            goal_event = GoalEventWS(
                fixture_id=fixture.fixture_id,
                league_id=fixture.league_id,
                league_name=fixture.league_name,
                home_team=fixture.home_team,
                away_team=fixture.away_team,
                team=goal.team,
                player=goal.player,
                minute=goal.minute,
                home_score=goal.home_score,
                away_score=goal.away_score,
                goal_type="Normal", # Polling usually doesn't give detailed type unless we parse events deeper
                timestamp=datetime.now()
            )
            
            await self._notify_goal_callbacks(goal_event)

    async def _notify_goal_callbacks(self, goal: GoalEventWS) -> None:
        for callback in self.goal_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(goal)
                else:
                    callback(goal)
            except Exception as e:
                logger.error(f"Goal callback error: {e}")

    async def _notify_fixture_callbacks(self, fixtures: List[LiveFixture]) -> None:
        for callback in self.fixture_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(fixtures)
                else:
                    callback(fixtures)
            except Exception as e:
                logger.error(f"Fixture callback error: {e}")

    def get_active_fixtures(self) -> List[Dict]:
        # Return dict representation for compatibility
        return [
            {
                "fixture": {"id": f.fixture_id, "status": {"short": f.status, "elapsed": f.minute}},
                "league": {"id": f.league_id, "name": f.league_name},
                "goals": {"home": f.home_score, "away": f.away_score},
                "teams": {"home": {"name": f.home_team}, "away": {"name": f.away_team}}
            }
            for f in self.active_fixtures.values()
        ]


class HybridGoalListener:
    """
    Wrapper for WebSocketGoalListener (now Polling).
    Kept for backward compatibility with Engine Unified.
    """
    
    def __init__(self, api_key: str = "") -> None:
        self.listener = WebSocketGoalListener(api_key)
        
    def register_goal_callback(self, callback: GoalCallback) -> None:
        self.listener.register_goal_callback(callback)

    def register_fixture_callback(self, callback: Callable[[List[LiveFixture]], Optional[Awaitable[None]]]) -> None:
        self.listener.register_fixture_callback(callback)

    async def start(self) -> None:
        await self.listener.start()

    async def stop(self) -> None:
        await self.listener.stop()

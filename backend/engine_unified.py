
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

# Import components
from bot.websocket_goal_listener import WebSocketGoalListener, HybridGoalListener, GoalEventWS
from alphas.alpha_one_underdog import AlphaOneUnderdog, TradingMode
from alphas.alpha_two_late_compression import AlphaTwoLateCompression
from exchanges.polymarket import PolymarketClient
from exchanges.kalshi import KalshiClient
from data.api_football import APIFootballClient

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# --- CONSTANTS ---

# Loop Intervals (Seconds)
INTERVAL_PRE_MATCH_ODDS = 1800  # 30 minutes
INTERVAL_ERROR_RETRY = 60       # 1 minute
INTERVAL_LIVE_FIXTURE = 30      # 30 seconds
INTERVAL_STATS_REPORT = 300     # 5 minutes

# Default Values
DEFAULT_MARKET_PRICE = 0.5
DEFAULT_ENABLE_WEBSOCKET = True
DEFAULT_ENABLE_ALPHA_ONE = True
DEFAULT_ENABLE_ALPHA_TWO = True

# Environment Variable Keys
ENV_TRADING_MODE = "TRADING_MODE"
ENV_ENABLE_ALPHA_ONE = "ENABLE_ALPHA_ONE"
ENV_ENABLE_ALPHA_TWO = "ENABLE_ALPHA_TWO"
ENV_ENABLE_WEBSOCKET = "ENABLE_WEBSOCKET"
ENV_API_FOOTBALL_KEY = "API_FOOTBALL_KEY"
ENV_POLYMARKET_API_KEY = "POLYMARKET_API_KEY"
ENV_KALSHI_API_KEY = "KALSHI_API_KEY"
ENV_KALSHI_API_SECRET = "KALSHI_API_SECRET"

# String Literals
MODE_SIMULATION = "simulation"
MODE_LIVE = "live"
VAL_TRUE = "true"
KEY_YES = "yes"
KEY_NO = "no"
STATUS_RESOLVED = "resolved"
STATUS_ACTIVE = "active"


@dataclass
class EngineConfig:
    mode: TradingMode = TradingMode.SIMULATION
    enable_alpha_one: bool = DEFAULT_ENABLE_ALPHA_ONE
    enable_alpha_two: bool = DEFAULT_ENABLE_ALPHA_TWO
    enable_websocket: bool = DEFAULT_ENABLE_WEBSOCKET
    
    api_football_key: str = ""
    polymarket_key: str = ""
    kalshi_key: str = ""
    kalshi_secret: str = ""
    
    @classmethod
    def from_env(cls) -> "EngineConfig":
        mode_str = os.getenv(ENV_TRADING_MODE, MODE_SIMULATION).lower()
        mode = TradingMode.LIVE if mode_str == MODE_LIVE else TradingMode.SIMULATION
        
        return cls(
            mode=mode,
            enable_alpha_one=os.getenv(ENV_ENABLE_ALPHA_ONE, VAL_TRUE).lower() == VAL_TRUE,
            enable_alpha_two=os.getenv(ENV_ENABLE_ALPHA_TWO, VAL_TRUE).lower() == VAL_TRUE,
            enable_websocket=os.getenv(ENV_ENABLE_WEBSOCKET, VAL_TRUE).lower() == VAL_TRUE,
            api_football_key=os.getenv(ENV_API_FOOTBALL_KEY, ""),
            polymarket_key=os.getenv(ENV_POLYMARKET_API_KEY, ""),
            kalshi_key=os.getenv(ENV_KALSHI_API_KEY, ""),
            kalshi_secret=os.getenv(ENV_KALSHI_API_SECRET, "")
        )


class UnifiedTradingEngine:
    """
    The main trading engine that orchestrates data ingestion, strategy execution, and trade management.

    This unified engine integrates multiple trading strategies (Alpha One, Alpha Two) with live
    data feeds via high-frequency polling. It supports both simulation and live trading modes.

    Key Features:
        - Real-time Goal Detection: Uses WebSocketGoalListener (currently implementing high-frequency
          polling, ~10s latency) for event updates. Note: The name "WebSocketGoalListener" is retained
          for legacy compatibility despite the underlying mechanism being polling.
        - Multi-Strategy Support:
            - Alpha One: Underdog Momentum (betting on underdogs taking the lead).
            - Alpha Two: Late-Stage Compression (betting on high-probability outcomes near match end).
        - Dual Operation Modes:
            - Simulation: Paper trading for backtesting strategies.
            - Live: Real-money trading on Polymarket and Kalshi.
        - Automatic Risk Management: Position sizing, stop-loss, and take-profit handling.

    Attributes:
        config (EngineConfig): Configuration parameters for the engine.
        polymarket (PolymarketClient): Client for interacting with Polymarket exchange.
        kalshi (KalshiClient): Client for interacting with Kalshi exchange.
        api_football (APIFootballClient): Client for fetching sports data.
        goal_listener (HybridGoalListener): Service for listening to real-time goal events.
    """
    
    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig.from_env()
        
        self.polymarket: Optional[PolymarketClient] = None
        self.kalshi: Optional[KalshiClient] = None
        self.api_football: Optional[APIFootballClient] = None
        
        if self.config.polymarket_key:
            self.polymarket = PolymarketClient()
        
        if self.config.kalshi_key:
            self.kalshi = KalshiClient()
        
        if self.config.api_football_key:
            self.api_football = APIFootballClient()
        
        self.goal_listener: Optional[HybridGoalListener] = None
        if self.config.enable_websocket:
            self.goal_listener = HybridGoalListener(self.config.api_football_key)
        
        self.alpha_one: Optional[AlphaOneUnderdog] = None
        self.alpha_two: Optional[AlphaTwoLateCompression] = None
        
        if self.config.enable_alpha_one:
            self.alpha_one = AlphaOneUnderdog(
                mode=self.config.mode,
                polymarket_client=self.polymarket,
                kalshi_client=self.kalshi
            )
        
        if self.config.enable_alpha_two:
            self.alpha_two = AlphaTwoLateCompression(
                polymarket_client=self.polymarket,
                kalshi_client=self.kalshi,
                simulation_mode=self.config.mode == TradingMode.SIMULATION
            )
        
        self.running = False
        self.start_time: Optional[datetime] = None
        
        self.goals_processed = 0
        self.signals_generated = 0
        
        logger.info("=" * 60)
        logger.info("UNIFIED TRADING ENGINE INITIALIZED")
        logger.info("=" * 60)
        logger.info(f"Mode: {self.config.mode.value.upper()}")
        logger.info(f"Alpha One (Underdog): {'ENABLED' if self.config.enable_alpha_one else 'DISABLED'}")
        logger.info(f"Alpha Two (Clipping): {'ENABLED' if self.config.enable_alpha_two else 'DISABLED'}")
        logger.info(f"WebSocket: {'ENABLED' if self.config.enable_websocket else 'DISABLED'}")
        logger.info(f"Polymarket: {'CONNECTED' if self.polymarket else 'NOT CONFIGURED'}")
        logger.info(f"Kalshi: {'CONNECTED' if self.kalshi else 'NOT CONFIGURED'}")
        logger.info("=" * 60)

    async def start(self):
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("Starting Unified Trading Engine...")
        
        if self.goal_listener and self.alpha_one:
            self.goal_listener.register_goal_callback(self._on_goal_event)
        
        tasks = []
        
        if self.goal_listener:
            tasks.append(asyncio.create_task(self.goal_listener.start()))
        
        if self.alpha_one:
            tasks.append(asyncio.create_task(self.alpha_one.monitor_positions()))
        
        if self.alpha_two:
            tasks.append(asyncio.create_task(self.alpha_two.start()))
        
       
        tasks.append(asyncio.create_task(self._pre_match_odds_loop()))
        
      
        tasks.append(asyncio.create_task(self._live_fixture_loop()))
        
       
        tasks.append(asyncio.create_task(self._stats_reporter_loop()))
        
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
        finally:
            await self.stop()

    async def stop(self):
        self.running = False
        
        if self.goal_listener:
            await self.goal_listener.stop()
        
        if self.alpha_two:
            await self.alpha_two.stop()
        
        if self.polymarket:
            await self.polymarket.close()
        
        if self.kalshi:
            await self.kalshi.close()
        
        logger.info("Unified Trading Engine stopped")
        
        #
        self._export_session_logs()

    async def _on_goal_event(self, goal: GoalEventWS):
        
        self.goals_processed += 1
        
        logger.info(f"Processing goal event: {goal.player} ({goal.team})")
        
        
        if self.alpha_one:
            signal = await self.alpha_one.on_goal_event(goal)
            
            if signal:
                self.signals_generated += 1
                logger.info(f"Alpha One signal generated: {signal.signal_id}")
        
        if self.alpha_two:
            fixture_data = {
                "fixture_id": goal.fixture_id,
                "market_id": f"fixture_{goal.fixture_id}_{goal.team}",
                "question": f"Will {goal.team} win?",
                "home_team": goal.home_team,
                "away_team": goal.away_team,
                "home_score": goal.home_score,
                "away_score": goal.away_score,
                "minute": goal.minute,
                "status": "2H" if goal.minute > 45 else "1H",
                "yes_price": DEFAULT_MARKET_PRICE,  # Would get from market
                "no_price": DEFAULT_MARKET_PRICE
            }
            await self.alpha_two.feed_live_fixture_update(fixture_data)

    async def _pre_match_odds_loop(self):
        while self.running:
            try:
                if self.api_football and self.alpha_one:
                    fixtures = await self._fetch_todays_fixtures()
                    
                    for fixture in fixtures:
                        fixture_id = fixture.get("fixture_id")
                        
                        odds = await self._fetch_pre_match_odds(fixture_id)
                        
                        if odds:
                            await self.alpha_one.cache_pre_match_odds(fixture_id, odds)
                
                await asyncio.sleep(INTERVAL_PRE_MATCH_ODDS)
                
            except Exception as e:
                logger.error(f"Pre-match odds loop error: {e}")
                await asyncio.sleep(INTERVAL_ERROR_RETRY)

    async def _fetch_todays_fixtures(self) -> List[Dict]:
        if not self.api_football:
            return []
        
        try:
            fixtures = await self.api_football.get_live_fixtures()
            return [{"fixture_id": f.fixture_id} for f in fixtures]
        except Exception as e:
            logger.error(f"Error fetching fixtures: {e}")
            return []

    async def _fetch_pre_match_odds(self, fixture_id: int) -> Optional[Dict[str, float]]:
        if self.polymarket:
            try:
               
                pass
            except Exception as e:
                logger.error(f"Error fetching Polymarket pre-match odds for fixture {fixture_id}: {e}")
        
        if self.api_football:
            try:
                return await self.api_football.get_pre_match_odds(fixture_id)
            except Exception as e:
                logger.error(f"Error fetching API-Football pre-match odds for fixture {fixture_id}: {e}")
        
        return None

    async def _live_fixture_loop(self):
        while self.running:
            try:
                if self.alpha_two and self.api_football:
                    fixtures = await self.api_football.get_live_fixtures()
                    
                    for fixture in fixtures:
                        market_prices = await self._get_fixture_market_prices(fixture)
                        
                        fixture_data = {
                            "fixture_id": fixture.fixture_id,
                            "market_id": f"fixture_{fixture.fixture_id}",
                            "question": f"Will {fixture.home_team} win?",
                            "home_team": fixture.home_team,
                            "away_team": fixture.away_team,
                            "home_score": fixture.home_score,
                            "away_score": fixture.away_score,
                            "minute": fixture.minute,
                            "status": fixture.status,
                            "yes_price": market_prices.get(KEY_YES, DEFAULT_MARKET_PRICE),
                            "no_price": market_prices.get(KEY_NO, DEFAULT_MARKET_PRICE)
                        }
                        
                        await self.alpha_two.feed_live_fixture_update(fixture_data)
                
                await asyncio.sleep(INTERVAL_LIVE_FIXTURE)
                
            except Exception as e:
                logger.error(f"Live fixture loop error: {e}")
                await asyncio.sleep(INTERVAL_LIVE_FIXTURE)

    async def _get_fixture_market_prices(self, fixture) -> Dict[str, float]:
        if not self.polymarket:
            return {KEY_YES: DEFAULT_MARKET_PRICE, KEY_NO: DEFAULT_MARKET_PRICE}

        event_name = f"{fixture.home_team} vs {fixture.away_team}"

        try:
            markets = await self.polymarket.get_markets_by_event(event_name)

            if not markets:
                logger.debug(f"No markets found for event: {event_name}")
                return {KEY_YES: DEFAULT_MARKET_PRICE, KEY_NO: DEFAULT_MARKET_PRICE}

            market = markets[0]
            token_id = market.get("clobTokenIds", [None])[0]

            if not token_id:
                logger.warning(f"No CLOB token ID found for market {market.get('id')} (Fixture: {fixture.fixture_id})")
                return {KEY_YES: DEFAULT_MARKET_PRICE, KEY_NO: DEFAULT_MARKET_PRICE}

            yes_price = await self.polymarket.get_yes_price(token_id)

            if yes_price:
                return {KEY_YES: yes_price, KEY_NO: 1 - yes_price}

            logger.warning(f"Price not found for token {token_id} (Fixture: {fixture.fixture_id})")

        except Exception as e:
            logger.error(f"Error fetching market prices for {event_name}: {e}", exc_info=True)
        
        return {KEY_YES: DEFAULT_MARKET_PRICE, KEY_NO: DEFAULT_MARKET_PRICE}

    async def _stats_reporter_loop(self):
        """Periodically report engine statistics"""
        while self.running:
            try:
                await asyncio.sleep(INTERVAL_STATS_REPORT)
                
                logger.info("=" * 40)
                logger.info("ENGINE STATISTICS")
                logger.info("=" * 40)
                
                if self.start_time:
                    uptime = (datetime.now() - self.start_time).total_seconds()
                    logger.info(f"Uptime: {uptime/60:.1f} minutes")
                
                logger.info(f"Goals Processed: {self.goals_processed}")
                logger.info(f"Signals Generated: {self.signals_generated}")
                
                if self.alpha_one:
                    stats = self.alpha_one.get_stats()
                    logger.info(f"Alpha One - Trades: {stats.total_trades}, Win Rate: {stats.win_rate:.1%}, P&L: ${stats.total_pnl:.2f}")
                
                if self.alpha_two:
                    stats = self.alpha_two.get_stats()
                    logger.info(f"Alpha Two - Trades: {stats.trades_executed}, Win Rate: {stats.win_rate:.1%}, P&L: ${stats.total_pnl:.2f}")
                
                logger.info("=" * 40)
                
            except Exception as e:
                logger.error(f"Stats reporter error: {e}")

    def _export_session_logs(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.alpha_one:
            self.alpha_one.export_event_log(f"logs/alpha_one_{timestamp}.json")
        
        if self.alpha_two:
            self.alpha_two.export_event_log(f"logs/alpha_two_{timestamp}.json")
        
        logger.info(f"Session logs exported with timestamp: {timestamp}")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Trading Engine")
    parser.add_argument(
        "--mode",
        choices=[MODE_SIMULATION, MODE_LIVE],
        default=MODE_SIMULATION,
        help="Trading mode"
    )
    parser.add_argument(
        "--alpha-one",
        action="store_true",
        default=True,
        help="Enable Alpha One (Underdog Strategy)"
    )
    parser.add_argument(
        "--alpha-two",
        action="store_true",
        default=True,
        help="Enable Alpha Two (Late Compression)"
    )
    parser.add_argument(
        "--no-websocket",
        action="store_true",
        help="Disable WebSocket (use polling fallback)"
    )
    
    args = parser.parse_args()
    
    config = EngineConfig.from_env()
    config.mode = TradingMode.LIVE if args.mode == MODE_LIVE else TradingMode.SIMULATION
    config.enable_alpha_one = args.alpha_one
    config.enable_alpha_two = args.alpha_two
    config.enable_websocket = not args.no_websocket
    
    engine = UnifiedTradingEngine(config)
    await engine.start()


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    
    asyncio.run(main())

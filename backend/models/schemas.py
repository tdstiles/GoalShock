"""
Data models for real-time soccer events and markets
"""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class GoalEvent(BaseModel):
    """Real-time goal event from live soccer match"""
    id: str = Field(..., description="Unique event ID")
    fixture_id: int = Field(..., description="API-Football fixture ID")
    timestamp: datetime = Field(default_factory=datetime.now)

    # Match info
    league_id: int
    league_name: str
    home_team: str
    away_team: str

    # Goal details
    team: str = Field(..., description="Team that scored")
    player: str = Field(..., description="Goal scorer")
    assist: Optional[str] = None
    minute: int = Field(..., description="Minute of goal")
    extra_time: Optional[int] = None
    goal_type: str = Field(default="Normal Goal")  # Normal Goal, Own Goal, Penalty

    # Current score
    home_score: int
    away_score: int

    # Market context
    market_ids: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "evt_123456",
                "fixture_id": 12345,
                "league_id": 39,
                "league_name": "Premier League",
                "home_team": "Manchester City",
                "away_team": "Liverpool",
                "team": "Liverpool",
                "player": "Salah",
                "minute": 67,
                "home_score": 1,
                "away_score": 2
            }
        }

class MarketPrice(BaseModel):
    """Real-time market price for soccer outcome"""
    market_id: str
    fixture_id: int
    question: str

    # Pricing
    yes_price: float = Field(..., ge=0.01, le=0.99)
    no_price: float = Field(..., ge=0.01, le=0.99)

    # Metadata
    source: str = Field(..., description="polymarket or kalshi")
    last_updated: datetime = Field(default_factory=datetime.now)
    volume_24h: Optional[float] = None
    liquidity: Optional[float] = None

    # Match context
    home_team: str
    away_team: str

    @property
    def is_stale(self) -> bool:
        """Check if price data is stale (>60 seconds old)"""
        from ..config.settings import settings
        age = (datetime.now() - self.last_updated).total_seconds()
        return age > settings.STALE_DATA_THRESHOLD

class LiveMatch(BaseModel):
    """Live soccer match data"""
    fixture_id: int
    league_id: int
    league_name: str

    home_team: str
    away_team: str
    home_score: int
    away_score: int

    minute: int
    status: str  # "1H", "HT", "2H", "ET", "P"

    timestamp: datetime = Field(default_factory=datetime.now)

    # Associated markets
    markets: List[MarketPrice] = Field(default_factory=list)

class MarketUpdate(BaseModel):
    """WebSocket market price update"""
    type: str = "market_update"
    market_id: str
    yes_price: float
    no_price: float
    timestamp: datetime = Field(default_factory=datetime.now)

class GoalAlert(BaseModel):
    """WebSocket goal alert to frontend"""
    type: str = "goal"
    goal: GoalEvent
    markets: List[MarketPrice] = Field(default_factory=list)

"""Unit tests for RealtimeIngestor parsing logic."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.bot.realtime_ingestor import RealtimeIngestor
from backend.models.schemas import GoalEvent

def build_full_fixture_data(
    home_team: str = "Home",
    away_team: str = "Away",
    home_score: int = 1,
    away_score: int = 0,
    events: list[Dict[str, Any]] | None = None
) -> Dict[str, Any]:
    """Helper to build a complete fixture data structure mimicking API-Football."""
    return {
        "fixture": {"id": 100, "status": {"short": "2H", "elapsed": 65}},
        "league": {"id": 39, "name": "Premier League"},
        "teams": {
            "home": {"name": home_team},
            "away": {"name": away_team}
        },
        "goals": {
            "home": home_score,
            "away": away_score
        },
        "events": events if events is not None else []
    }

def test_create_goal_event_happy_path():
    """Should correctly extract goal details from a valid event list."""
    ingestor = RealtimeIngestor()

    events = [
        {
            "time": {"elapsed": 10, "extra": None},
            "team": {"name": "Home"},
            "player": {"name": "Striker A"},
            "assist": {"name": "Midfielder B"},
            "type": "Goal",
            "detail": "Normal Goal"
        }
    ]

    data = build_full_fixture_data(events=events)

    goal = ingestor._create_goal_event(data, "Home", "home")

    assert goal is not None
    assert goal.player == "Striker A"
    assert goal.assist == "Midfielder B"
    assert goal.minute == 10
    assert goal.team == "Home"
    assert goal.home_score == 1
    assert goal.fixture_id == 100

def test_create_goal_event_extra_time():
    """Should correctly handle goals scored in extra time."""
    ingestor = RealtimeIngestor()

    events = [
        {
            "time": {"elapsed": 90, "extra": 4},
            "team": {"name": "Away"},
            "player": {"name": "Sub C"},
            "assist": {"name": None},
            "type": "Goal",
            "detail": "Normal Goal"
        }
    ]

    data = build_full_fixture_data(home_score=1, away_score=1, events=events)

    goal = ingestor._create_goal_event(data, "Away", "away")

    assert goal is not None
    assert goal.minute == 90
    assert goal.extra_time == 4
    assert goal.player == "Sub C"

def test_create_goal_event_filters_correct_team():
    """Should ignore goals from the opposing team."""
    ingestor = RealtimeIngestor()

    events = [
        # Goal for Home
        {
            "time": {"elapsed": 10, "extra": None},
            "team": {"name": "Home"},
            "player": {"name": "Striker A"},
            "type": "Goal",
            "detail": "Normal Goal"
        },
        # Goal for Away (latest in list)
        {
            "time": {"elapsed": 50, "extra": None},
            "team": {"name": "Away"},
            "player": {"name": "Striker B"},
            "type": "Goal",
            "detail": "Normal Goal"
        }
    ]

    data = build_full_fixture_data(events=events)

    # We ask for "Home" goal, should get the first one, not the last one in the list
    goal = ingestor._create_goal_event(data, "Home", "home")

    assert goal is not None
    assert goal.team == "Home"
    assert goal.player == "Striker A" # Should be the Home goal

def test_create_goal_event_no_events_found():
    """Should return None if the events array is empty."""
    ingestor = RealtimeIngestor()
    data = build_full_fixture_data(events=[])

    goal = ingestor._create_goal_event(data, "Home", "home")

    assert goal is None

def test_create_goal_event_no_matching_goal():
    """Should return None if events exist but none match the team/type."""
    ingestor = RealtimeIngestor()

    events = [
        {
            "time": {"elapsed": 10},
            "team": {"name": "Home"},
            "type": "Card", # Not a goal
            "detail": "Yellow Card"
        },
        {
            "time": {"elapsed": 20},
            "team": {"name": "Away"}, # Wrong team
            "type": "Goal",
            "detail": "Normal Goal"
        }
    ]

    data = build_full_fixture_data(events=events)

    goal = ingestor._create_goal_event(data, "Home", "home")

    assert goal is None

def test_create_goal_event_malformed_data_graceful_failure():
    """Should return None and log error instead of crashing on malformed data."""
    ingestor = RealtimeIngestor()

    # Missing 'player' key entirely
    events = [
        {
            "time": {"elapsed": 10},
            "team": {"name": "Home"},
            "type": "Goal",
            "detail": "Normal Goal"
             # 'player' key missing
        }
    ]

    data = build_full_fixture_data(events=events)

    # This should trigger the try-except block in _create_goal_event
    goal = ingestor._create_goal_event(data, "Home", "home")

    assert goal is None

def test_create_goal_event_picks_latest_goal():
    """Should pick the last goal in the list for the specified team."""
    ingestor = RealtimeIngestor()

    events = [
        {
            "time": {"elapsed": 10},
            "team": {"name": "Home"},
            "player": {"name": "First Scorer"},
            "type": "Goal",
            "detail": "Normal Goal"
        },
        {
            "time": {"elapsed": 85},
            "team": {"name": "Home"},
            "player": {"name": "Second Scorer"},
            "type": "Goal",
            "detail": "Normal Goal"
        }
    ]

    data = build_full_fixture_data(events=events)

    goal = ingestor._create_goal_event(data, "Home", "home")

    assert goal is not None
    assert goal.player == "Second Scorer"
    assert goal.minute == 85

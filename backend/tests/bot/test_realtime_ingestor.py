"""Unit tests for realtime ingestor goal detection."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, call

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.bot.realtime_ingestor import RealtimeIngestor
from backend.models.schemas import GoalEvent, LiveMatch


def build_live_match(home_score: int, away_score: int) -> LiveMatch:
    """Create a LiveMatch instance for tests."""
    return LiveMatch(
        fixture_id=1,
        league_id=10,
        league_name="Test League",
        home_team="Home",
        away_team="Away",
        home_score=home_score,
        away_score=away_score,
        minute=10,
        status="1H",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )


def build_goal_event(team: str, home_score: int, away_score: int, event_id: str) -> GoalEvent:
    """Create a GoalEvent sentinel for tests."""
    return GoalEvent(
        id=event_id,
        fixture_id=1,
        league_id=10,
        league_name="Test League",
        home_team="Home",
        away_team="Away",
        team=team,
        player="Scorer",
        assist=None,
        minute=10,
        extra_time=None,
        goal_type="Normal Goal",
        home_score=home_score,
        away_score=away_score,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )


def build_fixture_data() -> Dict:
    """Create fixture data input for _detect_new_goals."""
    return {"fixture": {"id": 1}}


def test_detect_new_goals_home_score_increase() -> None:
    """Detect a new home goal when the home score increases."""
    ingestor = RealtimeIngestor()
    old_match = build_live_match(home_score=0, away_score=0)
    new_match = build_live_match(home_score=1, away_score=0)
    fixture_data = build_fixture_data()
    home_goal = build_goal_event("Home", home_score=1, away_score=0, event_id="goal-home")

    ingestor._create_goal_event = MagicMock(return_value=home_goal)

    result = ingestor._detect_new_goals(old_match, new_match, fixture_data)

    assert result == [home_goal]
    ingestor._create_goal_event.assert_called_once_with(fixture_data, "Home", "home")


def test_detect_new_goals_away_score_increase() -> None:
    """Detect a new away goal when the away score increases."""
    ingestor = RealtimeIngestor()
    old_match = build_live_match(home_score=0, away_score=0)
    new_match = build_live_match(home_score=0, away_score=1)
    fixture_data = build_fixture_data()
    away_goal = build_goal_event("Away", home_score=0, away_score=1, event_id="goal-away")

    ingestor._create_goal_event = MagicMock(return_value=away_goal)

    result = ingestor._detect_new_goals(old_match, new_match, fixture_data)

    assert result == [away_goal]
    ingestor._create_goal_event.assert_called_once_with(fixture_data, "Away", "away")


def test_detect_new_goals_both_scores_increase() -> None:
    """Detect two goals when both teams' scores increase."""
    ingestor = RealtimeIngestor()
    old_match = build_live_match(home_score=0, away_score=0)
    new_match = build_live_match(home_score=1, away_score=1)
    fixture_data = build_fixture_data()
    home_goal = build_goal_event("Home", home_score=1, away_score=1, event_id="goal-home")
    away_goal = build_goal_event("Away", home_score=1, away_score=1, event_id="goal-away")

    ingestor._create_goal_event = MagicMock(side_effect=[home_goal, away_goal])

    result = ingestor._detect_new_goals(old_match, new_match, fixture_data)

    assert result == [home_goal, away_goal]
    ingestor._create_goal_event.assert_has_calls(
        [
            call(fixture_data, "Home", "home"),
            call(fixture_data, "Away", "away"),
        ]
    )


def test_detect_new_goals_no_score_change() -> None:
    """Return no goals when the score does not change."""
    ingestor = RealtimeIngestor()
    old_match = build_live_match(home_score=1, away_score=1)
    new_match = build_live_match(home_score=1, away_score=1)
    fixture_data = build_fixture_data()

    ingestor._create_goal_event = MagicMock()

    result = ingestor._detect_new_goals(old_match, new_match, fixture_data)

    assert result == []
    ingestor._create_goal_event.assert_not_called()

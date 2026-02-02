
import pytest
from backend.alphas.alpha_one_underdog import AlphaOneUnderdog

def test_map_odds_to_teams_substring_bug():
    alpha = AlphaOneUnderdog()

    # Case 1: Home team is substring of Away team
    home_team = "Inter"
    away_team = "Inter Miami"

    odds = {
        "Inter": 2.5,
        "Inter Miami": 3.0
    }

    mapped_odds = alpha._map_odds_to_teams(odds, home_team, away_team)

    assert mapped_odds.get(home_team) == 2.5
    assert mapped_odds.get(away_team) == 3.0

def test_map_odds_to_teams_generic_names():
    alpha = AlphaOneUnderdog()

    # Case 2: Generic names containing 'home' or 'away'
    home_team = "Go Away" # A team name containing 'Away'
    away_team = "Stay Home" # A team name containing 'Home'

    odds = {
        "Go Away": 1.5,
        "Stay Home": 4.0
    }

    mapped_odds = alpha._map_odds_to_teams(odds, home_team, away_team)

    assert mapped_odds.get(home_team) == 1.5
    assert mapped_odds.get(away_team) == 4.0

def test_map_odds_to_teams_keywords():
    alpha = AlphaOneUnderdog()

    home_team = "Team A"
    away_team = "Team B"

    odds = {
        "Home Win": 1.8,
        "Away Win": 2.1
    }

    mapped_odds = alpha._map_odds_to_teams(odds, home_team, away_team)

    assert mapped_odds.get(home_team) == 1.8
    assert mapped_odds.get(away_team) == 2.1

def test_map_odds_to_teams_exact_vs_partial():
    alpha = AlphaOneUnderdog()

    home_team = "Man City"
    away_team = "Man Utd"

    odds = {
        "Man City": 1.2,
        "Man Utd": 5.0
    }

    mapped_odds = alpha._map_odds_to_teams(odds, home_team, away_team)

    assert mapped_odds.get(home_team) == 1.2
    assert mapped_odds.get(away_team) == 5.0

def test_map_odds_to_teams_partial_overlap():
    alpha = AlphaOneUnderdog()

    home_team = "Real"
    away_team = "Real Madrid"

    # If odds keys are confusing
    odds = {
        "Real": 3.0,
        "Real Madrid": 1.5
    }

    mapped_odds = alpha._map_odds_to_teams(odds, home_team, away_team)

    assert mapped_odds.get(home_team) == 3.0
    assert mapped_odds.get(away_team) == 1.5

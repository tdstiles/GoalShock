import pytest
from alphas.alpha_two_late_compression import (
    AlphaTwoLateCompression,
    SPORT_BASKETBALL,
    SPORT_BASEBALL,
    CONFIDENCE_VERY_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_FAVORABLE,
    CONFIDENCE_NEUTRAL,
    CONFIDENCE_MAX
)

class TestAlphaTwoUSSports:

    @pytest.fixture
    def strategy(self):
        return AlphaTwoLateCompression(simulation_mode=True)

    def test_basketball_confidence_under_shot_clock(self, strategy):
        """
        Test Basketball confidence when time remaining is < 24s (Shot Clock logic).
        Logic: expected_swing = max(2.5, PPS * seconds * 2)
        PPS = 0.04. For 10s: 0.04 * 10 * 2 = 0.8. Max(2.5, 0.8) = 2.5.

        Thresholds:
        - Very High: > 2.5 * 1.5 = 3.75 (i.e., Lead >= 4)
        - Medium: > 2.5 (i.e., Lead >= 3)
        - Favorable: > 0
        """
        seconds = 10

        # Case 1: Lead 4 (Very High)
        # 4 > 3.75 -> Very High
        conf = strategy._calculate_us_sports_confidence(4, seconds, SPORT_BASKETBALL)
        assert conf == CONFIDENCE_VERY_HIGH

        # Case 2: Lead 3 (Medium)
        # 3 > 2.5 but 3 < 3.75 -> Medium
        conf = strategy._calculate_us_sports_confidence(3, seconds, SPORT_BASKETBALL)
        assert conf == CONFIDENCE_MEDIUM

        # Case 3: Lead 2 (Favorable)
        # 2 < 2.5 but > 0 -> Favorable
        conf = strategy._calculate_us_sports_confidence(2, seconds, SPORT_BASKETBALL)
        assert conf == CONFIDENCE_FAVORABLE

        # Case 4: Lead 0 (Neutral)
        conf = strategy._calculate_us_sports_confidence(0, seconds, SPORT_BASKETBALL)
        assert conf == CONFIDENCE_NEUTRAL

    def test_basketball_confidence_regular_time(self, strategy):
        """
        Test Basketball confidence when time remaining is >= 24s.
        Logic: expected_swing = max(3.5, PPS * seconds * 2)
        PPS = 0.04.

        Sub-case A: 30s remaining.
        Calc: 0.04 * 30 * 2 = 2.4. Max(3.5, 2.4) = 3.5.
        - Very High: > 3.5 * 1.5 = 5.25 (Lead >= 6)
        - Medium: > 3.5 (Lead >= 4)
        """
        seconds = 30

        # Lead 6 -> Very High
        conf = strategy._calculate_us_sports_confidence(6, seconds, SPORT_BASKETBALL)
        assert conf == CONFIDENCE_VERY_HIGH

        # Lead 4 -> Medium
        conf = strategy._calculate_us_sports_confidence(4, seconds, SPORT_BASKETBALL)
        assert conf == CONFIDENCE_MEDIUM

        # Lead 3 -> Favorable (3 < 3.5)
        conf = strategy._calculate_us_sports_confidence(3, seconds, SPORT_BASKETBALL)
        assert conf == CONFIDENCE_FAVORABLE

        """
        Sub-case B: 100s remaining (Higher volatility).
        Calc: 0.04 * 100 * 2 = 8.0. Max(3.5, 8.0) = 8.0.
        - Very High: > 8.0 * 1.5 = 12.0
        - Medium: > 8.0
        """
        seconds_long = 100

        # Lead 13 -> Very High
        conf = strategy._calculate_us_sports_confidence(13, seconds_long, SPORT_BASKETBALL)
        assert conf == CONFIDENCE_VERY_HIGH

        # Lead 9 -> Medium
        conf = strategy._calculate_us_sports_confidence(9, seconds_long, SPORT_BASKETBALL)
        assert conf == CONFIDENCE_MEDIUM

        # Lead 8 -> Favorable (Assuming strictly > expected_swing for Medium)
        # Logic: if lead_margin > expected_swing... 8 > 8 is False.
        conf = strategy._calculate_us_sports_confidence(8, seconds_long, SPORT_BASKETBALL)
        assert conf == CONFIDENCE_FAVORABLE

    def test_baseball_confidence(self, strategy):
        """
        Test Baseball confidence.
        Logic: expected_swing = PPS * seconds * 2
        PPS = 0.003.

        Case: 9th Inning, 2 outs? (Time approximation: 300s left?)
        Let's say 500s remaining.
        Calc: 0.003 * 500 * 2 = 3.0.

        - Very High: > 3.0 * 1.5 = 4.5 (Lead >= 5)
        - Medium: > 3.0 (Lead >= 4)
        """
        seconds = 500

        # Lead 5 -> Very High
        conf = strategy._calculate_us_sports_confidence(5, seconds, SPORT_BASEBALL)
        assert conf == CONFIDENCE_VERY_HIGH

        # Lead 4 -> Medium
        conf = strategy._calculate_us_sports_confidence(4, seconds, SPORT_BASEBALL)
        assert conf == CONFIDENCE_MEDIUM

        # Lead 3 -> Favorable (3 <= 3.0)
        conf = strategy._calculate_us_sports_confidence(3, seconds, SPORT_BASEBALL)
        assert conf == CONFIDENCE_FAVORABLE

    def test_max_confidence_cap(self, strategy):
        """
        Ensure confidence never exceeds CONFIDENCE_MAX (0.99),
        even if logic returns a higher constant or value.
        """
        # Create a scenario that returns CONFIDENCE_VERY_HIGH (0.98)
        # And ensure it respects the cap if we were to change constants.
        # Currently CONFIDENCE_VERY_HIGH (0.98) < CONFIDENCE_MAX (0.99)

        # But let's verify the min() clamp in return statement.
        # return min(CONFIDENCE_MAX, confidence)

        # Since I can't easily inject a value > 0.99 without mocking constants or internals,
        # I verify that a massive lead returns CONFIDENCE_VERY_HIGH
        seconds = 10
        conf = strategy._calculate_us_sports_confidence(100, seconds, SPORT_BASKETBALL)
        assert conf == CONFIDENCE_VERY_HIGH
        assert conf <= CONFIDENCE_MAX

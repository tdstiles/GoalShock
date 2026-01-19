
import pytest
from backend.alphas.alpha_one_underdog import AlphaOneUnderdog

def test_alpha_one_confidence_logic_inversion():
    """
    Sherlock Logic Check:
    Verifies that the strategy has higher confidence in 'Stronger' underdogs
    (those with higher pre-match probability) when they take the lead,
    compared to 'Weaker' underdogs (low probability).

    Current Bug: The logic '1 - (odds/threshold)' inverts this, giving
    highest confidence to the weakest teams.
    """
    alpha = AlphaOneUnderdog()

    # Case A: Weak Underdog (1% chance to win pre-match)
    # They score and lead by 1.
    odds_weak = 0.01
    conf_weak = alpha._calculate_confidence(
        pre_match_odds=odds_weak,
        minute=30,
        lead_margin=1
    )

    # Case B: Strong Underdog (40% chance to win pre-match)
    # They score and lead by 1.
    odds_strong = 0.40
    conf_strong = alpha._calculate_confidence(
        pre_match_odds=odds_strong,
        minute=30,
        lead_margin=1
    )

    print(f"\nWeak Underdog (1%) Confidence: {conf_weak:.4f}")
    print(f"Strong Underdog (40%) Confidence: {conf_strong:.4f}")

    # We expect the Strong Underdog to inspire more confidence than the Weak one
    assert conf_strong > conf_weak, (
        f"Logical Error: Strategy prefers weaker underdogs! "
        f"Strong({conf_strong:.4f}) should be > Weak({conf_weak:.4f})"
    )

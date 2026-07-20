"""
Elasticity module:
Handles customer demand sensitivity calculations
"""

def calculate_elasticity(price_change, volume_change):
    """
    Calculate elasticity = % volume change / % price change

    Parameters:
    price_change (float): The percentage change in price.
    volume_change (float): The percentage change in volume.

    Returns:
    float: The elasticity value, or 0.0 if price_change is zero.
    """
    if price_change == 0:
        return 0.0          # No price change → no elasticity to measure
    return volume_change / price_change

# (upper_bound_exclusive, adjustment, tier_label) — checked in order, first
# match wins. elasticity == 0.0 is handled separately (see elasticity_tier/
# elasticity_adjustment) since it's also what a suppressed/no-signal category
# reports (too few transactions to trust — see generate_reports.build_pricing
# _input's MIN_ELASTICITY_UNITS), and that must never be confused with a
# genuinely-measured, strongly-inelastic 0.0.
_TIERS = [
    (-3.0, -0.03, "Very Elastic"),
    (-1.5, -0.02, "Elastic"),
    (-1.2, -0.01, "Mildly Elastic"),
    (-0.8, 0.0, "Unit Elastic"),
    (0.0, 0.01, "Inelastic"),
    (1.5, 0.02, "Very Inelastic"),
    (float("inf"), 0.03, "Highly Inelastic"),
]
NO_SIGNAL_TIER = "No Signal"


def elasticity_tier(elasticity: float) -> str:
    """Human-readable label for the elasticity bin — shown in the UI so the
    reasoning behind an adjustment is visible, not just the raw number."""
    if elasticity == 0.0:
        return NO_SIGNAL_TIER
    for upper_bound, _, label in _TIERS:
        if elasticity < upper_bound:
            return label
    return _TIERS[-1][2]


def elasticity_adjustment(elasticity):
    """
    Convert elasticity into a pricing adjustment, capped at +/-3%. Bins are
    centered on elasticity = -1 (unit-elastic): more elastic (price-sensitive)
    -> cut price to protect volume; more inelastic or positively correlated
    (volume doesn't fall, or even rises, with price) -> raise price to capture
    the pricing power. A narrow hold zone around -1 (-1.2 to -0.8) avoids
    flipping between a cut and a raise on a marginal difference near the
    boundary. elasticity == 0.0 always means "no signal" (see NO_SIGNAL_TIER)
    and gets no adjustment, regardless of which bin it would otherwise fall in.
    """
    if elasticity == 0.0:
        return 0.0
    for upper_bound, adjustment, _ in _TIERS:
        if elasticity < upper_bound:
            return adjustment
    return _TIERS[-1][1]
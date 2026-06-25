"""
Market module:
Handles competitor-based price adjustments
"""

def market_adjustment(base_price, comp_min, comp_max):
    """
    Adjust price based on competitor positioning.

    Parameters:
    base_price (float): The base price of the product.
    comp_min (float): The minimum price among competitors.
    comp_max (float): The maximum price among competitors.

    Returns:
    float: The adjustment factor to be applied to the base price.
    """
    market_avg = (comp_min + comp_max) / 2

    if market_avg == 0:
        return 0

    price_gap = (base_price - market_avg) / market_avg

    # Validate price_gap to ensure it is a valid number
    if not isinstance(price_gap, (int, float)):
        raise ValueError("price_gap must be a numeric value")

    if price_gap > 0.10:
        return -0.03
    elif price_gap > 0.05:
        return -0.02
    elif price_gap > -0.05:
        return 0.0
    elif price_gap > -0.10:
        return 0.01
    else:
        return 0.02
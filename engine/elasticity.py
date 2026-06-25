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

def elasticity_adjustment(elasticity):
    """
    Convert elasticity into pricing adjustment
    """
    thresholds = {
        -1.5: -0.03,
        -0.8: -0.02,
        -0.3: -0.01
    }
    for threshold, adjustment in sorted(thresholds.items()):
        if elasticity < threshold:
            return adjustment
    return 0.0
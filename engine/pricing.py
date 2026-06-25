"""
Pricing engine:
Combines base price, elasticity, and market adjustments
"""

from engine.elasticity import calculate_elasticity, elasticity_adjustment
from engine.market import market_adjustment


def calculate_price(product_data):
    """
    Main pricing function
    """

    # Step 1: Base price
    base_price = product_data["current_price"] * (
        1 + product_data["inflation"] + product_data["cost_change"]
    )

    # Step 2: Elasticity
    elasticity = calculate_elasticity(
        product_data["last_price_change"],
        product_data["volume_change"]
    )

    elasticity_adj = elasticity_adjustment(elasticity)

    # Step 3: Market adjustment
    market_adj = market_adjustment(
        base_price,
        product_data["comp_min"],
        product_data["comp_max"]
    )

    # Step 4: Final price
    final_price = base_price * (1 + elasticity_adj + market_adj)

    return {
        "product": product_data["product"],
        "base_price": round(base_price, 2),
        "elasticity": round(elasticity, 2),
        "elasticity_adj": round(elasticity_adj, 3),
        "market_adj": round(market_adj, 3),
        "final_price": round(final_price, 2),
    }
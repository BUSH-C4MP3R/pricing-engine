"""
Pricing engine:
Combines base price and elasticity adjustments
"""

from engine.elasticity import calculate_elasticity, elasticity_adjustment


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

    # Step 3: Final price
    final_price = base_price * (1 + elasticity_adj)

    # Step 4: Total adjustment (all factors combined)
    total_adj = (
        product_data["inflation"]      # macro cost pressure
        + product_data["cost_change"]  # input cost change
        + elasticity_adj               # demand sensitivity
    )

    return {
        "product": product_data["product"],
        "base_price": round(base_price, 2),
        "inflation_adj": round(product_data["inflation"], 3),
        "cost_change_adj": round(product_data["cost_change"], 3),
        "elasticity": round(elasticity, 2),
        "elasticity_adj": round(elasticity_adj, 3),
        "total_adj": round(total_adj, 3),
        "final_price": round(final_price, 2),
    }
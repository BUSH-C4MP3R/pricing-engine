"""
Pricing engine:
Combines base price and elasticity adjustments
"""

from engine.elasticity import calculate_elasticity, elasticity_adjustment, elasticity_tier


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

    # Step 3: Total adjustment + final price
    total_adj = product_data["inflation"] + product_data["cost_change"] + elasticity_adj
    final_price = product_data["current_price"] * (1 + total_adj)

    return {
        "product": product_data["product"],
        "current_price": round(product_data["current_price"], 2),
        "inflation": round(product_data["inflation"], 3),
        "cost_change": round(product_data["cost_change"], 3),
        "elasticity": round(elasticity, 2),
        "elasticity_tier": elasticity_tier(elasticity),
        "elasticity_adj": round(elasticity_adj, 3),
        "total_adj": round(total_adj, 3),
        "final_price": round(final_price, 2),
    }
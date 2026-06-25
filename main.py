
"""
Entry point: loads mock product inputs and prints pricing results.
Swap load_mock_inputs() for the RAG loader later.
"""

import json
import os
from engine.pricing import calculate_price

# Default dataset location (resolves relative to this file).
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "products.json")


def load_mock_inputs(path: str = DATA_PATH) -> list:
    """Load product inputs from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    print("=" * 60)
    print("PRODUCT PRICING ENGINE — RESULTS")
    print("=" * 60)
    for product_data in load_mock_inputs():
        r = calculate_price(product_data)
        print(f"\nProduct:         {r['product']}")
        print(f"  Base Price:    ${r['base_price']:.2f}")
        print(f"  Inflation Adj:  {r['inflation_adj'] * 100:+.1f}%")
        print(f"  Cost Change:    {r['cost_change_adj'] * 100:+.1f}%")
        print(f"  Elasticity:    {r['elasticity']}")
        print(f"  Elasticity Adj:{r['elasticity_adj'] * 100:+.1f}%")
        print(f"  Market Adj:    {r['market_adj'] * 100:+.1f}%")
        print(f"  ─────────────────────────────")
        print(f"  Total Adj:     {r['total_adj'] * 100:+.1f}%")
        print(f"  Final Price:   ${r['final_price']:.2f}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
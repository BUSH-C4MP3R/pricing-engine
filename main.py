"""
To run this script from the command line, use the following command:

brew services start ollama

ollama list 
(to see available models)

cd "/Users/satyajithbavisetty/Pricing Engine/Biologics_Pricing_Model"
source venv/bin/activate 
(to activate the virtual environment)

cat data/documents/biologics_a_report.txt
(show source document)

python -m tests.manual_retrieval_check
(to run the manual retrieval check test)

python pipeline.py
(to run the pipeline script)

cat output/pricing_results.json
(show the output results)

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

# ...existing code...

def main():
    # Queries — one per product you want to price
    queries = [
        "Biologics-A pricing inputs",
        "Biologics-B pricing inputs",
        "Biologics-C pricing inputs",
    ]

    results = run_all_products(queries)

    # Save the full batch as a JSON array
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    # Pretty-print (mirrors your main.py formatting)
    print("\n" + "=" * 60)
    print("RAG PRICING PIPELINE — RESULTS")
    print("=" * 60)
    for r in results:
        print(f"\nProduct:         {r['product']}")
        print(f"  Base Price:    ${r['base_price']:.2f}")
        print(f"  Total Adj:     {r['total_adj'] * 100:+.1f}%")
        print(f"  Final Price:   ${r['final_price']:.2f}")
    print("\n" + "=" * 60)
    print(f"Saved {len(results)} products to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
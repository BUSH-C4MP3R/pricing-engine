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
from pipeline import run_all_products, OUTPUT_PATH   # ← import batch fn + path

REPORTS_PATH = os.path.join(os.path.dirname(__file__), "data", "reports")


def discover_queries() -> list[str]:
    """Build one query per generated product report — scales automatically."""
    queries = []
    for fname in sorted(os.listdir(REPORTS_PATH)):
        if fname.endswith(".txt"):
            code = fname.replace("product_", "").replace(".txt", "")
            queries.append(f"{code} pricing inputs")
    return queries

def main():
    queries = discover_queries()                     # ← was hardcoded 3 products
    print(f"Found {len(queries)} product reports to price.\n")

    results = run_all_products(queries)

    # Save the full batch as a JSON array
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)   # ← fixes \u2014

    print("\n" + "=" * 60)
    print("RAG PRICING PIPELINE — RESULTS")
    print("=" * 60)
    for r in results:
        print(f"\nProduct:         {r['product']}")
        print(f"  Current Price: ${r['current_price']:.2f}")   # ← was base_price
        print(f"  Total Adj:     {r['total_adj'] * 100:+.1f}%")
        print(f"  Final Price:   ${r['final_price']:.2f}")
    print("\n" + "=" * 60)
    print(f"Saved {len(results)} products to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
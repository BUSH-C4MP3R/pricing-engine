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
from pipeline import run_all_reports, OUTPUT_PATH   # ← was run_all_products

REPORTS_PATH = os.path.join(os.path.dirname(__file__), "data", "reports")


def discover_reports() -> list[str]:
    """Return FULL PATHS to each report — no fuzzy queries, no duplicates."""
    return [
        os.path.join(REPORTS_PATH, f)
        for f in sorted(os.listdir(REPORTS_PATH))
        if f.endswith(".txt")
    ]


def main():
    reports = discover_reports()                     # ← was discover_queries()
    print(f"Found {len(reports)} product reports to price.\n")

    results = run_all_reports(reports)               # ← was run_all_products(queries)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("RAG PRICING PIPELINE — RESULTS")
    print("=" * 60)
    for r in results:
        print(f"\nProduct:         {r['product']}")
        print(f"  Current Price: ${r['current_price']:.2f}")
        print(f"  Total Adj:     {r['total_adj'] * 100:+.1f}%")
        print(f"  Final Price:   ${r['final_price']:.2f}")
    print("\n" + "=" * 60)
    print(f"Saved {len(results)} products to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
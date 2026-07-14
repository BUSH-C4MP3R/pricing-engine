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
from pipeline import run_all_categories, OUTPUT_PATH


def main():
    results = run_all_categories()
    print(f"Priced {len(results)} categories.\n")

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
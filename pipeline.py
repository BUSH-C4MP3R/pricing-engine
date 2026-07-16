"""
Full pipeline: pandas (CSV) -> structured pricing inputs
              + RAG/LLM (macro PDFs) -> macro factors
              -> validate -> deterministic pricing engine.

Pandas-derived numbers (current_price, last_price_change, volume_change)
flow straight from generate_reports.build_pricing_input() into the pricing
engine — RAG + LLM extraction is reserved for the macro PDFs in data/macro,
the only genuinely unstructured source in this pipeline.

Run with:  python3 pipeline.py
"""

import json
import os

from generate_reports import CSV, load_and_clean, build_pricing_input
from rag.ingest import load_documents, chunk_text
from rag.vectorstore import VectorStore
from rag.extractor import extract_macro_data
from rag.schema import validate_product
from engine.categories import is_priceable
from engine.pricing import calculate_price

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output", "pricing_results.json")

DEFAULT_INFLATION = 0.03

# The macro cost-change concept has been retired — the inflation report gives
# one combined rate per category, so cost_change is no longer a separate
# tracked input (always 0.0; inflation carries the full macro effect).
MACRO_BUCKETS = ("Instruments", "Consumables", "Service")


def macro_bucket(cat: str) -> str:
    """'Maurice / Consumables - Cart' -> 'Consumables' — the inflation report
    only breaks rates out by Instruments/Consumables/Service, not by product
    line or sub-category, so that's the granularity we match macro docs against."""
    category = cat.split(" / ", 1)[1]
    if category == "Units":
        return "Instruments"
    if category.startswith("Consumables"):
        return "Consumables"
    return "Service"  # covers "Service" and "Service Contracts"


# Plausibility guard: this business's inflation/cost commentary never runs
# above ~25%. Extraction mistakes (unit errors, misplaced decimals) tend to
# produce wildly larger numbers, so anything above this is dropped rather
# than silently fed into pricing.
MAX_PLAUSIBLE_INFLATION = 0.25


def _clean_macro(raw: dict, buckets: list[str]) -> dict:
    """Keep only well-formed {bucket: inflation} entries for buckets we
    actually asked about — anything else the LLM invents is dropped.
    raw values are {"low": pct, "high": pct} (plain percentages, e.g. 4 for
    4%); the midpoint and percent->decimal conversion happen here in Python,
    not in the LLM, since that arithmetic is where extraction went wrong."""
    cleaned = {}
    for bucket in buckets:
        entry = raw.get(bucket)
        if not isinstance(entry, dict):
            continue
        low, high = entry.get("low"), entry.get("high")
        if not (isinstance(low, (int, float)) and isinstance(high, (int, float))):
            continue
        inflation = (float(low) + float(high)) / 2 / 100
        if 0 <= inflation <= MAX_PLAUSIBLE_INFLATION:
            cleaned[bucket] = inflation
    return cleaned


def get_macro_factors(buckets: list[str] = MACRO_BUCKETS) -> dict:
    """Extract a combined inflation rate per bucket (Instruments/Consumables/
    Service) from macro docs via RAG+LLM. Buckets not found in the docs are
    simply absent — price_category() falls back to DEFAULT_INFLATION for those."""
    macro_docs = load_documents()
    if not macro_docs:
        print("⚠️  No macro docs found — using default inflation for all categories")
        return {}

    chunks = [c for doc in macro_docs for c in chunk_text(doc)]
    store = VectorStore()
    store.build(chunks)                              # only macro doc content embedded
    context = "\n".join(
        store.retrieve("inflation rate by product category", k=10)
    )
    raw = extract_macro_data(context, list(buckets))
    macro = _clean_macro(raw, list(buckets))
    print(f"📊 Inflation extracted for {len(macro)}/{len(buckets)} categories: {macro}")
    return macro


def price_category(df, cat: str, macro_by_bucket: dict) -> dict:
    """Price ONE category: pandas gives current_price and the instrument-
    specific historical price/volume change; the inflation report gives the
    bucket's combined rate."""
    data = build_pricing_input(df, cat)
    if data is None:
        raise ValueError(f"Not enough yearly history to price '{cat}'")
    data["inflation"] = macro_by_bucket.get(macro_bucket(cat), DEFAULT_INFLATION)
    data["cost_change"] = 0.0
    clean_data = validate_product(data)
    return calculate_price(clean_data)


def run_all_categories() -> list[dict]:
    """Price every priceable category — each gets its own instrument-specific
    historical price change, plus its bucket's combined inflation rate."""
    df = load_and_clean(CSV)
    cats = sorted(
        c for c in df["ProdGroup"].unique() if "Other" not in c and is_priceable(c)
    )
    macro_by_bucket = get_macro_factors()

    results = []
    for cat in cats:
        try:
            results.append(price_category(df, cat, macro_by_bucket))
            print(f"✅ Priced: {cat}")
        except (ValueError, TypeError) as e:
            print(f"⚠️  Skipped '{cat}': {e}")
    return results


def main():
    results = run_all_categories()

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    print("Pricing results:")
    print(json.dumps(results, indent=4))
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

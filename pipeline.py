"""
Full RAG -> LLM -> deterministic pricing pipeline.

Run with:  python3 pipeline.py
"""

import json
import os

from rag.ingest import load_documents, chunk_text
from rag.vectorstore import VectorStore
from rag.extractor import extract_product_data
from rag.schema import validate_product
from engine.pricing import calculate_price

REPORTS_PATH = os.path.join(os.path.dirname(__file__), "data", "reports")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output", "pricing_results.json")

def build_vector_store() -> VectorStore:
    """Load, chunk, and embed all documents ONCE."""
    docs = load_documents()
    chunks = [c for doc in docs for c in chunk_text(doc)]
    store = VectorStore()
    store.build(chunks)
    return store


def price_product(store: VectorStore, product_query: str) -> dict:
    """Run ONE product query against an already-built store."""
    context = "\n".join(store.retrieve(product_query))
    raw_data = extract_product_data(context)
    clean_data = validate_product(raw_data)
    return calculate_price(clean_data)

def price_report_file(filepath: str) -> dict:
    """Price ONE known report by reading it DIRECTLY — no fuzzy retrieval."""
    with open(filepath, "r", encoding="utf-8") as f:
        context = f.read()                       # ← the exact file, guaranteed
    raw_data = extract_product_data(context)     # LLM still parses the numbers
    clean_data = validate_product(raw_data)
    return calculate_price(clean_data)


def run_all_reports(report_files: list[str]) -> list[dict]:
    """Price MANY reports, each read directly from disk (deterministic)."""
    results = []
    for path in report_files:
        name = os.path.basename(path)
        try:
            results.append(price_report_file(path))
            print(f"✅ Priced: {name}")
        except (ValueError, TypeError) as e:
            print(f"⚠️  Skipped '{name}': {e}")
    return results

def run_pipeline(product_query: str) -> dict:
    """Convenience: build store + price a single product."""
    store = build_vector_store()
    return price_product(store, product_query)


def run_all_products(queries: list[str]) -> list[dict]:
    """Price MANY products, embedding the corpus only once."""
    store = build_vector_store()          # expensive step — done once
    results = []
    for q in queries:
        try:
            results.append(price_product(store, q))
            print(f"✅ Priced: {q}")
        except (ValueError, TypeError) as e:
            print(f"⚠️  Skipped '{q}': {e}")
    return results

def main():
    query = "Biologics-A pricing inputs"
    result = run_pipeline(query)

    # Save to the output folder you already have
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print("Pricing result:")
    print(json.dumps(result, indent=4))
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
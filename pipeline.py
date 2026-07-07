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

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output", "pricing_results.json")


def run_pipeline(product_query: str) -> dict:
    # 1. Ingest & chunk documents
    docs = load_documents()
    chunks = [c for doc in docs for c in chunk_text(doc)]

    # 2. Build vector store & retrieve relevant context
    store = VectorStore()
    store.build(chunks)
    context = "\n".join(store.retrieve(product_query))

    # 3. LLM extracts structured inputs (no math)
    raw_data = extract_product_data(context)

    # 4. Validate before it touches the engine
    clean_data = validate_product(raw_data)

    # 5. Deterministic pricing (unchanged engine)
    return calculate_price(clean_data)


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
"""Manual sanity check for retrieval quality (no LLM needed)."""

from rag.ingest import load_documents, chunk_text
from rag.vectorstore import VectorStore

docs = load_documents()
chunks = [c for doc in docs for c in chunk_text(doc)]

store = VectorStore()
store.build(chunks)

results = store.retrieve("Biologics-A current price and inflation", k=2)
print("Top retrieved chunks:\n")
for i, chunk in enumerate(results, 1):
    print(f"[{i}] {chunk}\n")

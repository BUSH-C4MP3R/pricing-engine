"""
Embed chunks and retrieve the most relevant context for a query.
Uses FAISS (local) + sentence-transformers (local embeddings).
"""

import faiss
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")


class VectorStore:
    def __init__(self):
        self.chunks: list[str] = []
        self.index = None

    def build(self, chunks: list[str]):
        """Embed chunks and build the FAISS index."""
        if not chunks:
            raise ValueError("No chunks provided to build the index.")
        self.chunks = chunks
        embeddings = _model.encode(chunks, convert_to_numpy=True)
        self.index = faiss.IndexFlatL2(embeddings.shape[1])
        self.index.add(embeddings)

    def retrieve(self, query: str, k: int = 3) -> list[str]:
        """Return the top-k most relevant chunks for a query."""
        query_vec = _model.encode([query], convert_to_numpy=True)
        k = min(k, len(self.chunks))
        _, indices = self.index.search(query_vec, k)
        return [self.chunks[i] for i in indices[0]]
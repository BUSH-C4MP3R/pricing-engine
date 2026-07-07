"""
Load source documents and split them into retrievable chunks.
Drop your .txt source files into data/documents/.
"""

import os

DOCS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "documents")


def load_documents(folder: str = DOCS_PATH) -> list[str]:
    """Read all .txt files in the documents folder."""
    texts = []
    for filename in os.listdir(folder):
        if filename.endswith(".txt"):
            with open(os.path.join(folder, filename), encoding="utf-8") as f:
                texts.append(f.read())
    return texts


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping word chunks for embedding."""
    words = text.split()
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks
"""
Load macro PDFs/text (inflation, cost-change commentary) and chunk them.
This is the ONLY unstructured source RAG operates on — pandas-derived
sales numbers flow straight into pricing without ever passing through here.
The raw sales CSV is NEVER read here — only pandas touches that.
"""

import os
from pypdf import PdfReader

BASE = os.path.dirname(__file__)
MACRO_PATH = os.path.join(BASE, "..", "data", "macro")


def _load_txt(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _load_pdf(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


LOADERS = {".txt": _load_txt, ".pdf": _load_pdf}


def load_documents() -> list[str]:
    """Read macro PDFs/text into raw text."""
    texts = []
    if os.path.isdir(MACRO_PATH):
        for fname in os.listdir(MACRO_PATH):
            ext = os.path.splitext(fname)[1].lower()
            loader = LOADERS.get(ext)
            if loader:
                try:
                    texts.append(loader(os.path.join(MACRO_PATH, fname)))
                except Exception as e:
                    print(f"⚠️  Skipped {fname}: {e}")
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
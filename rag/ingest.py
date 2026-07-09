"""
Load prose documents (generated reports + macro PDFs) and chunk them.
The raw sales CSV is NEVER read here — only pandas touches that.
"""

import os
import pandas as pd
from pypdf import PdfReader

BASE = os.path.dirname(__file__)
REPORTS_PATH = os.path.join(BASE, "..", "data", "reports")
MACRO_PATH = os.path.join(BASE, "..", "data", "macro")


def _load_txt(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _load_pdf(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


LOADERS = {".txt": _load_txt, ".pdf": _load_pdf}


def load_documents() -> list[str]:
    """Read generated reports + macro PDFs into text."""
    texts = []
    for folder in (REPORTS_PATH, MACRO_PATH):
        if not os.path.isdir(folder):
            continue
        for fname in os.listdir(folder):
            ext = os.path.splitext(fname)[1].lower()
            loader = LOADERS.get(ext)
            if loader:
                try:
                    texts.append(loader(os.path.join(folder, fname)))
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
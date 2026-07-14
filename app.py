"""
Streamlit dashboard for the Biologics Pricing Engine.
Run with:  streamlit run app.py
"""

import json
import os

import streamlit as st

from generate_reports import CSV, load_and_clean, load_reference_prices
from pipeline import (
    DEFAULT_INFLATION,
    MACRO_BUCKETS,
    OUTPUT_PATH,
    get_macro_factors,
    price_category,
)
from rag.ingest import MACRO_PATH

st.set_page_config(page_title="Biologics Pricing Engine", layout="wide")
st.title("Biologics Pricing Model")


@st.cache_data
def _load_df():
    return load_and_clean(CSV)


def _categories(df):
    return sorted(c for c in df["ProdGroup"].unique() if "Other" not in c)


if "macro_extracted" not in st.session_state:
    st.session_state.macro_extracted = {}
if "macro_docs_signature" not in st.session_state:
    st.session_state.macro_docs_signature = None
if "results" not in st.session_state:
    st.session_state.results = None


def _macro_docs_signature():
    """(filename, mtime) pairs for everything in data/macro — used to detect
    when documents were added/removed/changed so we know to re-extract."""
    if not os.path.isdir(MACRO_PATH):
        return ()
    return tuple(
        sorted(
            (f, os.path.getmtime(os.path.join(MACRO_PATH, f)))
            for f in os.listdir(MACRO_PATH)
            if f.lower().endswith((".pdf", ".txt"))
        )
    )

if st.sidebar.button("🔄 Reload sales CSV"):
    _load_df.clear()
    st.rerun()

df = _load_df()
cats = _categories(df)
reference_prices = load_reference_prices()

# ---------------- Sidebar: macro documents ----------------
st.sidebar.header("Macro Documents")
st.sidebar.caption(f"RAG reads PDFs/text from `{os.path.relpath(MACRO_PATH)}`")

os.makedirs(MACRO_PATH, exist_ok=True)
existing_files = sorted(
    f for f in os.listdir(MACRO_PATH) if f.lower().endswith((".pdf", ".txt"))
)
if existing_files:
    for fname in existing_files:
        col1, col2 = st.sidebar.columns([4, 1])
        col1.write(f"📄 {fname}")
        if col2.button("🗑", key=f"del_{fname}"):
            os.remove(os.path.join(MACRO_PATH, fname))
            st.rerun()
else:
    st.sidebar.caption("No macro documents yet.")

uploaded = st.sidebar.file_uploader(
    "Add PDF/.txt macro documents", type=["pdf", "txt"], accept_multiple_files=True
)
if uploaded:
    for file in uploaded:
        safe_name = os.path.basename(file.name)
        with open(os.path.join(MACRO_PATH, safe_name), "wb") as f:
            f.write(file.getbuffer())
    st.sidebar.success(f"Saved {len(uploaded)} file(s). Extracting macro factors...")
    st.rerun()

force_reextract = st.sidebar.button("🔍 Re-extract macro factors from documents")

current_signature = _macro_docs_signature()
docs_changed = current_signature != st.session_state.macro_docs_signature
if current_signature and (docs_changed or force_reextract):
    with st.spinner("Embedding documents and extracting via local LLM..."):
        st.session_state.macro_extracted = get_macro_factors()
        st.session_state.macro_docs_signature = current_signature
elif not current_signature:
    st.session_state.macro_extracted = {}
    st.session_state.macro_docs_signature = current_signature

# ---------------- Inflation rate: inspect + override ----------------
st.subheader("Inflation Rate")

macro_final = {}
cols = st.columns(len(MACRO_BUCKETS))
for col, bucket in zip(cols, MACRO_BUCKETS):
    extracted = st.session_state.macro_extracted.get(bucket)
    default_value = extracted if extracted is not None else DEFAULT_INFLATION

    with col:
        st.markdown(f"**{bucket}**")
        st.caption("extracted" if extracted is not None else "_default_")
        inflation = st.number_input(
            "Inflation", value=float(default_value), step=0.005, format="%.3f",
            key=f"inflation_{bucket}",
        )
    macro_final[bucket] = inflation

# ---------------- Run pipeline ----------------
if st.button("▶️ Run Pricing", type="primary"):
    with st.spinner("Pricing all categories..."):
        results = []
        for cat in cats:
            try:
                results.append(price_category(df, cat, macro_final, reference_prices))
            except (ValueError, TypeError) as e:
                st.warning(f"Skipped '{cat}': {e}")
        st.session_state.results = results
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
    st.success(f"Priced {len(results)} categories.")

# ---------------- Results ----------------
results = st.session_state.results
if results is None and os.path.exists(OUTPUT_PATH):
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        results = json.load(f)

if results:
    st.subheader("Pricing Summary")
    st.dataframe(results, use_container_width=True)

    st.subheader("Detailed Breakdown")
    for r in results:
        with st.expander(f"{r['product']}  →  Final Price: ${r['final_price']:.2f}"):
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Price", f"${r['current_price']:.2f}")
            col1.metric("Inflation", f"{r['inflation'] * 100:+.1f}%")
            col2.metric("Elasticity", f"{r['elasticity']}")
            col2.metric("Elasticity Adj", f"{r['elasticity_adj'] * 100:+.1f}%")
            col3.metric("Total Adjustment", f"{r['total_adj'] * 100:+.1f}%")
else:
    st.info("No pricing results yet — click 'Run Pricing' above.")

"""
Streamlit dashboard for the Biologics Pricing Engine.
Run with:  streamlit run app.py
"""

import base64
import json
import os

import streamlit as st

from generate_reports import CSV, load_and_clean
from pipeline import (
    DEFAULT_INFLATION,
    MACRO_BUCKETS,
    OUTPUT_PATH,
    get_macro_factors,
    price_category,
)
from engine.categories import is_priceable
from rag.ingest import MACRO_PATH

st.set_page_config(page_title="Biologics Pricing Engine", layout="wide")

# R&D Systems by Bio-Techne logo (pulled from resources.bio-techne.com/
# bio-techne-assets/images/homepage/rnd-by-bt-logo.svg — BT-Blue fill, so it
# reads on the plain page background rather than needing a dark bar behind
# it) — base64-encoded into a data: URI <img> tag rather than inlined as raw
# <svg> markup: the raw multi-line XML confused Streamlit's markdown
# HTML-block detection and got rendered as literal escaped text instead of
# an actual image.
_LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "rd-systems-by-bio-techne-logo.svg")
with open(_LOGO_PATH, "rb") as _f:
    _LOGO_B64 = base64.b64encode(_f.read()).decode("ascii")
_LOGO_IMG = '<img src="data:image/svg+xml;base64,{}" class="bt-logo" alt="R&amp;D Systems by Bio-Techne">'.format(_LOGO_B64)

# Bio-Techne brand palette (sourced from bio-techne.com's own CSS: bg-bt-blue /
# text-bt-blue / bg-dark-bt-blue / --Light-Blue utility classes) — the base
# widget theme lives in .streamlit/config.toml, this covers the masthead and
# tab accents that config.toml's theme keys can't reach. Font is Inter, the
# same body/heading typeface bio-techne.com itself uses (their site loads it
# as self-hosted "inter_regular"/"inter_bold" — Inter is open-source, so we
# pull it from Google Fonts instead of hotlinking their private CDN copy).
_HEADER_HTML = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body {
        font-family: 'Inter', sans-serif;
    }
    /* Fix the block-container's own side padding to a known value so the
    topbar/header below can cancel it exactly (negative margin == this
    padding) and truly reach the edges of the main content pane, rather than
    guessing at whatever Streamlit's default padding happens to be. */
    [data-testid="stMainBlockContainer"] {
        padding-left: 2rem;
        padding-right: 2rem;
    }
    .bt-topbar {
        display: flex;
        justify-content: flex-start;
        padding: 0.25rem 2rem 0.75rem 2rem;
        margin-left: -2rem;
        margin-right: -2rem;
    }
    .bt-topbar .bt-logo {
        height: 44px;
        width: auto;
        display: block;
    }
    .bt-header {
        background-color: #0034b7;
        padding: 1.5rem 2rem;
        margin-left: -2rem;
        margin-right: -2rem;
        margin-bottom: 1.5rem;
    }
    .bt-header h1 {
        color: #ffffff;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #e8eaf0;
        border-radius: 6px 6px 0 0;
        padding: 8px 20px;
    }
    .stTabs [data-baseweb="tab"] p {
        color: #0034b7;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #0034b7 !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] p {
        color: #ffffff !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #0034b7 !important;
    }
    [data-testid="stMetricValue"] {
        color: #0034b7;
    }
    h4 {
        color: #0034b7;
    }
    [data-testid="stExpander"] {
        border-left: 4px solid #0034b7;
        border-radius: 4px;
    }
    [data-testid="stSidebar"] {
        background-color: #e8eaf0;
    }
    </style>
    <div class="bt-topbar">__LOGO__</div>
    <div class="bt-header"><h1>Biologics Pricing Model</h1></div>
    """
st.markdown(_HEADER_HTML.replace("__LOGO__", _LOGO_IMG), unsafe_allow_html=True)


@st.cache_data
def _load_df():
    return load_and_clean(CSV)


# Display order for the UI (summary table + detail cards) — anything
# priceable but not listed here is appended after, sorted alphabetically.
# Service Contracts sits right before its respective Service category (for
# both Maurice and iCE3) — alphabetical order alone would put "Service"
# before "Service Contracts", the opposite of what's wanted here.
CATEGORY_ORDER = [
    "Maurice S. / Units",
    "Maurice C. / Units",
    "Maurice / Units",
    "Maurice Flex / Units",
    "Maurice / Consumables",
    "Maurice CE-SDS / Consumables",
    "Maurice CE-SDS / Consumables - Cart",
    "Maurice icIEF / Consumables",
    "Maurice icIEF / Consumables - Cart",
    "Maurice / Service Contracts",
    "Maurice / Service",
    "iCE3 / Consumables - Cart",
    "iCE3 / Consumables",
    "iCE3 / Service Contracts",
    "iCE3 / Service",
]


def _categories(df):
    available = {c for c in df["ProdGroup"].unique() if "Other" not in c and is_priceable(c)}
    ordered = [c for c in CATEGORY_ORDER if c in available]
    remaining = sorted(available - set(CATEGORY_ORDER))
    return ordered + remaining


def _sort_results(results):
    """Apply CATEGORY_ORDER to a results list regardless of where it came
    from — a fresh run already comes out in order, but results loaded from
    OUTPUT_PATH (written by pipeline.py's own alphabetical run) don't."""
    order_index = {cat: i for i, cat in enumerate(CATEGORY_ORDER)}
    return sorted(results, key=lambda r: (order_index.get(r["product"], len(CATEGORY_ORDER)), r["product"]))


def _product_line(cat: str) -> str:
    """'Maurice CE-SDS / Consumables' -> 'Maurice'; 'iCE3 / Service' -> 'iCE3'.
    Only Maurice* and iCE3 lines are ever priceable (MFI/Other are excluded
    upstream), so a simple prefix check is sufficient."""
    return "Maurice" if cat.startswith("Maurice") else "iCE3"


CATEGORY_GROUPS = {
    "Units": "Units",
    "Consumables": "Consumables",
    "Consumables - Cart": "Consumables",
    "Service Contracts": "Service & Contracts",
    "Service": "Service & Contracts",
}
GROUP_ORDER = ["Units", "Consumables", "Service & Contracts"]


def _category_group(cat: str) -> str:
    _, _, suffix = cat.partition(" / ")
    return CATEGORY_GROUPS.get(suffix, suffix)


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
        inflation = st.number_input(
            f"**{bucket}**", value=float(default_value), step=0.005, format="%.3f",
            key=f"inflation_{bucket}",
        )
    macro_final[bucket] = inflation

# ---------------- Run pipeline ----------------
if st.button("▶️ Run Pricing", type="primary"):
    with st.spinner("Pricing all categories..."):
        results = []
        for cat in cats:
            try:
                results.append(price_category(df, cat, macro_final))
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
    results = _sort_results(results)
    tab_maurice, tab_ice3 = st.tabs(["Maurice", "iCE3"])
    for tab, line in ((tab_maurice, "Maurice"), (tab_ice3, "iCE3")):
        with tab:
            line_results = [r for r in results if _product_line(r["product"]) == line]
            if not line_results:
                st.info(f"No priced categories for {line}.")
                continue
            for group in GROUP_ORDER:
                group_results = [r for r in line_results if _category_group(r["product"]) == group]
                if not group_results:
                    continue
                st.markdown(f"#### {group}")
                summary_rows = [{k: v for k, v in r.items() if k != "cost_change"} for r in group_results]
                st.dataframe(summary_rows, use_container_width=True)
                for r in group_results:
                    with st.expander(f"{r['product']}  →  Final Price: ${r['final_price']:.2f}"):
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Current Price", f"${r['current_price']:.2f}")
                        col1.metric("Inflation", f"{r['inflation'] * 100:+.1f}%")
                        col2.metric("Elasticity", f"{r['elasticity']}", help=r["elasticity_tier"])
                        col2.metric("Elasticity Adj", f"{r['elasticity_adj'] * 100:+.1f}%")
                        col3.metric("Total Adjustment", f"{r['total_adj'] * 100:+.1f}%")
                        col3.metric("Elasticity Tier", r["elasticity_tier"])
else:
    st.info("No pricing results yet — click 'Run Pricing' above.")

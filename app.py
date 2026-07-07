"""
Streamlit dashboard for the Biologics Pricing Engine.
Run with:  streamlit run app.py
"""

import streamlit as st
from engine.pricing import calculate_price
from main import load_mock_inputs

st.set_page_config(page_title="Biologics Pricing Engine", layout="wide")

st.title("Biologics Pricing Model")
st.caption("Deterministic, rule-based pricing results")

# Load products and price each one
products = load_mock_inputs()
results = [calculate_price(p) for p in products]

# Show as a table
st.subheader("Pricing Summary")
st.dataframe(results, use_container_width=True)

# Show detailed cards per product
st.subheader("Detailed Breakdown")
for r in results:
    with st.expander(f"{r['product']}  →  Final Price: ${r['final_price']:.2f}"):
        col1, col2, col3 = st.columns(3)
        col1.metric("Base Price", f"${r['base_price']:.2f}")
        col1.metric("Inflation Adj", f"{r['inflation_adj'] * 100:+.1f}%")
        col2.metric("Cost Change", f"{r['cost_change_adj'] * 100:+.1f}%")
        col2.metric("Elasticity", f"{r['elasticity']}")
        col3.metric("Elasticity Adj", f"{r['elasticity_adj'] * 100:+.1f}%")
        st.metric("Total Adjustment", f"{r['total_adj'] * 100:+.1f}%")
"""
Turn the raw sales CSV into per-category pricing inputs (structured, via
build_pricing_input) and human-readable prose reports (write_report).
pandas does the math (deterministic) — the pricing engine reads the
structured dict directly; the .txt files are for humans, not RAG.

Run:  python generate_reports.py
"""

import os
import pandas as pd
from engine.categories import classify

CSV = "data/sales/Biologics Sales Data_2020-2026.csv"
OUT = "data/reports"
REFERENCE_PRICES_CSV = "data/reference_prices.csv"


def load_reference_prices(path: str = REFERENCE_PRICES_CSV) -> dict:
    """List/catalog prices per ProdGroup (e.g. CY26 pricing proposal), used as
    current_price instead of the CSV-derived average selling price where
    available. Categories not in this file fall back to the historical
    average (see build_pricing_input)."""
    if not os.path.exists(path):
        return {}
    ref = pd.read_csv(path)
    return dict(zip(ref["ProdGroup"], ref["ListPrice"]))


def load_and_clean(path: str) -> pd.DataFrame:
    """Load the CSV, drop junk, add Year + Category columns."""
    df = pd.read_csv(path)

    # drop footer / blank dates
    df = df[df["OrderDate"].notna()]
    df = df[~df["OrderDate"].astype(str).str.startswith("Exported")]

    # types
    df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
    df["ShippedQty"] = pd.to_numeric(df["ShippedQty"], errors="coerce")
    df["ReportingSalesPrice"] = pd.to_numeric(
        df["ReportingSalesPrice"], errors="coerce")
    df = df.dropna(subset=["OrderDate", "ShippedQty", "ReportingSalesPrice"])

    # real positive sales only
    df = df[(df["ShippedQty"] > 0) & (df["ReportingSalesPrice"] > 0)]

    df["Year"] = df["OrderDate"].dt.year
    df["ProdGroup"] = df.apply(classify, axis=1)      
    return df


def category_yearly(df: pd.DataFrame, cat: str) -> pd.DataFrame:
    c = df[df["ProdGroup"] == cat]                    
    yearly = c.groupby("Year").agg(
        revenue=("ReportingSalesPrice", "sum"),
        units=("ShippedQty", "sum"),
    )
    yearly["avg_price"] = yearly["revenue"] / yearly["units"]
    return yearly.sort_index()


def _safe(name: str) -> str:
    """'Maurice / Consumables' -> 'Maurice_Consumables' for a filename."""
    return name.replace(" / ", "_").replace(" ", "").replace("-", "")


def build_pricing_input(df: pd.DataFrame, cat: str, reference_prices: dict | None = None) -> dict | None:
    """Structured pricing input straight from pandas — no prose/LLM round-trip.

    current_price uses the list price from reference_prices (e.g. a CY26
    pricing proposal) when available for this category; otherwise it falls
    back to the CSV-derived historical average selling price. Either way,
    last_price_change/volume_change are always computed from the actual
    historical CSV trend.

    Returns None if there isn't enough yearly history to compute a change.
    'inflation' is filled in by pipeline.get_macro_factors(); 'cost_change' is
    always 0.0 (retired as a separate input — see pipeline.price_category).
    """
    reference_prices = reference_prices or {}
    yearly = category_yearly(df, cat)
    complete = yearly[yearly.index < pd.Timestamp.now().year]
    if len(complete) < 2:
        return None

    latest, prior = complete.iloc[-1], complete.iloc[-2]
    price_chg = (latest["avg_price"] - prior["avg_price"]) / prior["avg_price"]
    vol_chg = (latest["units"] - prior["units"]) / prior["units"]
    current_price = reference_prices.get(cat, latest["avg_price"])

    return {
        "product": cat,
        "current_price": float(current_price),
        "last_price_change": float(price_chg),
        "volume_change": float(vol_chg),
        "year": int(complete.index[-1]),
    }


def write_report(df: pd.DataFrame, cat: str, reference_prices: dict | None = None) -> bool:
    """Write a human-readable prose report. Reporting artifact only —
    the pricing engine reads build_pricing_input() directly, not this file."""
    data = build_pricing_input(df, cat, reference_prices)
    if data is None:
        return False

    report = f"""Product Report: {cat}

The current price for {cat} is ${data['current_price']:.2f} per unit (FY{data['year']}).
Macro inflation is running at 3% (0.03).
Input manufacturing costs increased by 2% (0.02).
The last price change applied was {data['last_price_change']*100:.0f}% ({data['last_price_change']:.2f}) year-over-year.
Following that change, unit volume moved {data['volume_change']*100:.0f}% ({data['volume_change']:.2f}) versus the prior year.
"""
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/product_{_safe(cat)}.txt", "w", encoding="utf-8") as f:
        f.write(report)
    return True


def main():
    df = load_and_clean(CSV)
    reference_prices = load_reference_prices()
    cats = sorted(c for c in df["ProdGroup"].unique() if "Other" not in c)  # ← was df["Category"]
    written = sum(write_report(df, cat, reference_prices) for cat in cats)
    print(f"✅ Wrote {written} category reports to {OUT}/")
    print("   Next: run python main.py")


if __name__ == "__main__":
    main()
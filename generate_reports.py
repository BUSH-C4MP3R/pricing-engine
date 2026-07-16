"""
Turn the raw sales CSV into per-category pricing inputs (structured, via
build_pricing_input) and human-readable prose reports (write_report).
pandas does the math (deterministic) — the pricing engine reads the
structured dict directly; the .txt files are for humans, not RAG.

Run:  python generate_reports.py
"""

import os
import pandas as pd
from engine.categories import classify, resolve_shared_items

CSV = "data/sales/Biologics Sales Data_2020-2026.csv"
OUT = "data/reports"
MIN_YEAR = 2022  # drop 2020-2021 — older data adds noise, not signal


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
    df = df[df["Year"] >= MIN_YEAR]
    df["ProdGroup"] = df.apply(classify, axis=1)
    df = resolve_shared_items(df)
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


MIN_PARTIAL_YEAR_COVERAGE = 0.5  # require >= 50% of the prorated expected volume


def build_pricing_input(df: pd.DataFrame, cat: str) -> dict | None:
    """Structured pricing input straight from pandas — no prose/LLM round-trip.

    current_price is the average selling price from the most recent available
    year of data, including the current (partial) year — so it's genuinely
    current rather than lagging a year behind. But for low-volume categories a
    partial year can be just a couple of transactions, which isn't
    representative: if the partial year's unit count is less than
    MIN_PARTIAL_YEAR_COVERAGE of what the prior complete year's pace would
    predict for the same elapsed time, we fall back to the latest complete
    year instead. last_price_change/volume_change (elasticity inputs) are
    always computed from the last two COMPLETE years, since comparing a
    partial year to a full year would distort the trend.

    Returns None if there isn't enough yearly history to compute a change.
    'inflation' is filled in by pipeline.get_macro_factors(); 'cost_change' is
    always 0.0 (retired as a separate input — see pipeline.price_category).
    """
    now = pd.Timestamp.now()
    yearly = category_yearly(df, cat)
    complete = yearly[yearly.index < now.year]
    if len(complete) < 2:
        return None

    latest_complete, prior = complete.iloc[-1], complete.iloc[-2]
    price_chg = (latest_complete["avg_price"] - prior["avg_price"]) / prior["avg_price"]
    vol_chg = (latest_complete["units"] - prior["units"]) / prior["units"]

    most_recent = yearly.iloc[-1]  # may be the current, partial year
    if int(most_recent.name) == now.year:
        elapsed_fraction = now.dayofyear / 365
        expected_units = latest_complete["units"] * elapsed_fraction
        if most_recent["units"] < MIN_PARTIAL_YEAR_COVERAGE * expected_units:
            most_recent = latest_complete  # too few sales so far this year to trust

    return {
        "product": cat,
        "current_price": float(most_recent["avg_price"]),
        "last_price_change": float(price_chg),
        "volume_change": float(vol_chg),
        "year": int(most_recent.name),
    }


def write_report(df: pd.DataFrame, cat: str) -> bool:
    """Write a human-readable prose report. Reporting artifact only —
    the pricing engine reads build_pricing_input() directly, not this file."""
    data = build_pricing_input(df, cat)
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
    cats = sorted(c for c in df["ProdGroup"].unique() if "Other" not in c)  # ← was df["Category"]
    written = sum(write_report(df, cat) for cat in cats)
    print(f"✅ Wrote {written} category reports to {OUT}/")
    print("   Next: run python main.py")


if __name__ == "__main__":
    main()
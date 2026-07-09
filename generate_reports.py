"""
Turn the raw sales CSV into small per-product prose reports.
pandas does the math (deterministic); RAG later reads the .txt output.

Run:  python generate_reports.py
"""

import os
import pandas as pd

CSV = "data/sales/Biologics Sales Data_2020-2026.csv"
OUT = "data/reports"
TOP_N = 15                             # only report highest-revenue products
INFLATION, COST_CHANGE = 0.03, 0.02    # placeholder — later from macro PDFs


def load_and_clean(path: str) -> pd.DataFrame:
    """Load CSV and apply all data-quality rules."""
    df = pd.read_csv(path)

    # Rule 1: drop junk export footer + blank date rows
    df = df[df["OrderDate"].notna()]
    df = df[~df["OrderDate"].astype(str).str.startswith("Exported")]

    # Rule 2: correct types
    df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
    df["ShippedQty"] = pd.to_numeric(df["ShippedQty"], errors="coerce")
    df["ReportingSalesPrice"] = pd.to_numeric(
        df["ReportingSalesPrice"], errors="coerce")
    df = df.dropna(subset=["OrderDate", "ShippedQty",
                           "ReportingSalesPrice", "ItemCode"])

    # Rule 3: drop returns / credit notes (negatives) + zero-shipped
    df = df[(df["ShippedQty"] > 0) & (df["ReportingSalesPrice"] > 0)]

    df["Year"] = df["OrderDate"].dt.year
    return df


def product_yearly(df: pd.DataFrame, item_code: str) -> pd.DataFrame:
    """Aggregate one product's transactions into a per-year table."""
    p = df[df["ItemCode"] == item_code]
    yearly = p.groupby("Year").agg(
        revenue=("ReportingSalesPrice", "sum"),   # USD line totals
        units=("ShippedQty", "sum"),
    )
    yearly["avg_price"] = yearly["revenue"] / yearly["units"]  # unit price
    return yearly.sort_index()


def write_report(df: pd.DataFrame, item_code: str) -> bool:
    """Write one prose report if the product has >= 2 complete years."""
    yearly = product_yearly(df, item_code)
    if len(yearly) < 2:
        return False

    # Skip the current partial year (e.g. 2026) so YoY is fair.
    complete = yearly[yearly.index < pd.Timestamp.now().year]
    if len(complete) < 2:
        complete = yearly                      # fallback if little history
    latest, prior = complete.iloc[-1], complete.iloc[-2]

    price_chg = (latest["avg_price"] - prior["avg_price"]) / prior["avg_price"]
    vol_chg = (latest["units"] - prior["units"]) / prior["units"]

    desc = str(df[df["ItemCode"] == item_code]["ItemDesc"].iloc[-1])
    year = int(complete.index[-1])

    report = f"""Product Report: {item_code} — {desc}

The current average selling price for {item_code} is ${latest['avg_price']:.2f} per unit (FY{year}).
Macro inflation is running at {INFLATION*100:.0f}% ({INFLATION}).
Input manufacturing costs increased by {COST_CHANGE*100:.0f}% ({COST_CHANGE}).
The last price change applied was {price_chg*100:.0f}% ({price_chg:.2f}) year-over-year.
Following that change, unit volume moved {vol_chg*100:.0f}% ({vol_chg:.2f}) versus the prior year.
"""
    os.makedirs(OUT, exist_ok=True)
    safe = item_code.replace("/", "-")
    with open(f"{OUT}/product_{safe}.txt", "w", encoding="utf-8") as f:
        f.write(report)
    return True


def main():
    df = load_and_clean(CSV)

    top = (df.groupby("ItemCode")["ReportingSalesPrice"]
             .sum().sort_values(ascending=False).head(TOP_N).index)

    written = sum(write_report(df, code) for code in top)
    print(f"✅ Wrote {written} reports to {OUT}/")
    print("   Next: run python pipeline.py")


if __name__ == "__main__":
    main()
"""
Turn the raw sales CSV into per-category prose reports.
pandas does the math (deterministic); RAG later reads the .txt output.

Run:  python generate_reports.py
"""

import os
import pandas as pd
from engine.categories import classify

CSV = "data/sales/Biologics Sales Data_2020-2026.csv"
OUT = "data/reports"


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


def write_report(df: pd.DataFrame, cat: str) -> bool:
    yearly = category_yearly(df, cat)
    complete = yearly[yearly.index < pd.Timestamp.now().year]
    if len(complete) < 2:
        return False

    latest, prior = complete.iloc[-1], complete.iloc[-2]
    price_chg = (latest["avg_price"] - prior["avg_price"]) / prior["avg_price"]
    vol_chg = (latest["units"] - prior["units"]) / prior["units"]
    year = int(complete.index[-1])

    report = f"""Product Report: {cat}

The current average selling price for {cat} is ${latest['avg_price']:.2f} per unit (FY{year}).
Macro inflation is running at 3% (0.03).
Input manufacturing costs increased by 2% (0.02).
The last price change applied was {price_chg*100:.0f}% ({price_chg:.2f}) year-over-year.
Following that change, unit volume moved {vol_chg*100:.0f}% ({vol_chg:.2f}) versus the prior year.
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
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


def item_yearly(df: pd.DataFrame, cat: str) -> pd.DataFrame:
    """Per-item (ItemDesc) yearly revenue/units/avg_price within a category —
    the basis for a same-item price change that isn't distorted by which SKU
    happened to sell more in a given year (see weighted_price_change)."""
    c = df[df["ProdGroup"] == cat]
    yearly = c.groupby(["ItemDesc", "Year"]).agg(
        revenue=("ReportingSalesPrice", "sum"),
        units=("ShippedQty", "sum"),
    )
    yearly["avg_price"] = yearly["revenue"] / yearly["units"]
    return yearly


def weighted_price_change(df: pd.DataFrame, cat: str, latest_year: int, prior_year: int,
                           fallback: float) -> float:
    """Revenue-weighted average of each item's OWN price change between two
    years, instead of the blended category average price ratio. A category
    with multiple SKUs at different price points can show a big swing in its
    blended average purely from the sales mix shifting toward a cheaper or
    pricier SKU, even if no item's own price moved — this avoids that by
    comparing each item to itself and weighting by its prior-year revenue.
    Items not present in both years are excluded (matched-sample index).
    Falls back to `fallback` (the blended ratio) if no items match."""
    items = item_yearly(df, cat)
    weighted_sum = 0.0
    total_weight = 0.0
    for item_desc in items.index.get_level_values("ItemDesc").unique():
        if (item_desc, prior_year) not in items.index or (item_desc, latest_year) not in items.index:
            continue
        prior_row = items.loc[(item_desc, prior_year)]
        latest_row = items.loc[(item_desc, latest_year)]
        if prior_row["avg_price"] == 0:
            continue
        item_price_chg = (latest_row["avg_price"] - prior_row["avg_price"]) / prior_row["avg_price"]
        weight = prior_row["revenue"]
        weighted_sum += item_price_chg * weight
        total_weight += weight
    return weighted_sum / total_weight if total_weight else fallback


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
    year instead.

    last_price_change/volume_change (elasticity inputs) compare the latest
    complete year against the CURRENT year (annualized to a full-year
    run-rate) rather than the last two complete years, so the trend reflects
    the most recent year rather than one that's already a year stale.
    Annualizing only matters for volume_change (units is an absolute count
    that needs scaling to be comparable to a full year) — last_price_change
    is a ratio (avg_price = revenue/units) that's already unaffected by how
    much of the year has elapsed. If the current year has no data at all yet,
    falls back to comparing the last two complete years instead.
    last_price_change uses weighted_price_change() (a same-item price index)
    rather than the blended category average, so a shift in sales mix between
    SKUs at different price points doesn't get misread as a price change.

    Returns None if there isn't enough yearly history to compute a change.
    'inflation' is filled in by pipeline.get_macro_factors(); 'cost_change' is
    always 0.0 (retired as a separate input — see pipeline.price_category).
    """
    now = pd.Timestamp.now()
    yearly = category_yearly(df, cat)
    complete = yearly[yearly.index < now.year]
    if len(complete) < 1:
        return None

    baseline, baseline_year = complete.iloc[-1], int(complete.index[-1])  # last complete year

    if now.year in yearly.index:
        current = yearly.loc[now.year]
        elapsed_fraction = now.dayofyear / 365
        annualized_units = current["units"] / elapsed_fraction
        vol_chg = (annualized_units - baseline["units"]) / baseline["units"]
        blended_price_chg = (current["avg_price"] - baseline["avg_price"]) / baseline["avg_price"]
        price_chg = weighted_price_change(df, cat, now.year, baseline_year, fallback=blended_price_chg)
    elif len(complete) >= 2:
        prior, prior_year = complete.iloc[-2], int(complete.index[-2])
        vol_chg = (baseline["units"] - prior["units"]) / prior["units"]
        blended_price_chg = (baseline["avg_price"] - prior["avg_price"]) / prior["avg_price"]
        price_chg = weighted_price_change(df, cat, baseline_year, prior_year, fallback=blended_price_chg)
    else:
        return None

    most_recent = yearly.iloc[-1]  # may be the current, partial year
    if int(most_recent.name) == now.year:
        elapsed_fraction = now.dayofyear / 365
        expected_units = baseline["units"] * elapsed_fraction
        if most_recent["units"] < MIN_PARTIAL_YEAR_COVERAGE * expected_units:
            most_recent = baseline  # too few sales so far this year to trust

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
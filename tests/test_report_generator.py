"""Tests for the sales-cleaning logic in generate_reports.py."""

import pandas as pd
from generate_reports import load_and_clean, product_yearly


def _write_csv(tmp_path):
    """Create a tiny CSV with a good row, a credit note, and a zero-qty row."""
    csv = tmp_path / "sales.csv"
    csv.write_text(
        "OrderDate,ItemCode,ItemDesc,ShippedQty,ReportingSalesPrice\n"
        "1/1/2024 12:00:00 AM,004-001,Widget,1,100\n"
        "1/1/2025 12:00:00 AM,004-001,Widget,2,240\n"
        "1/1/2025 12:00:00 AM,004-001,Widget CN,-1,-120\n"   # credit note
        "1/1/2025 12:00:00 AM,004-001,Widget,0,0\n"          # zero shipped
        "Exported data exceeded the allowed volume.,,,,\n"    # junk footer
    )
    return str(csv)


def test_credit_notes_and_zero_qty_removed(tmp_path):
    df = load_and_clean(_write_csv(tmp_path))
    assert (df["ShippedQty"] > 0).all()
    assert (df["ReportingSalesPrice"] > 0).all()


def test_junk_footer_removed(tmp_path):
    df = load_and_clean(_write_csv(tmp_path))
    assert not df["OrderDate"].astype(str).str.startswith("Exported").any()


def test_yearly_unit_price(tmp_path):
    df = load_and_clean(_write_csv(tmp_path))
    yearly = product_yearly(df, "004-001")
    # 2025: 2 units for $240 total -> $120/unit
    assert round(yearly.loc[2025, "avg_price"], 2) == 120.00
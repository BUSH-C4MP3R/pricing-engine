"""Map raw transactions to the CY26 taxonomy: 'ProductLine / Category'."""


def product_line(desc: str) -> str:
    """iCE3 / Maurice / MFI — detected from the ItemDesc product name."""
    d = str(desc).lower()
    if "maurice" in d:                       # covers 'Maurice' + 'MauriceFlex'
        return "Maurice"
    if "mfi" in d:
        return "MFI"
    if "ice" in d:                           # covers 'iCE3', 'iCE280', 'iCE System'
        return "iCE3"
    return "Other"


def category(inst_cons_svc: str, desc: str = "") -> str:
    """Units / Consumables / Service (+ sub-splits)."""
    s, d = str(inst_cons_svc).lower(), str(desc).lower()

    if "instrument" in s or "unit" in s:
        return "Units"
    if "service" in s:
        return "Service Contracts" if ("contract" in d or "plan" in d) else "Service"
    if "consumable" in s:
        if "cart" in d:
            return "Consumables - Cart"
        return "Consumables"
    return "Other"


def classify(row) -> str:
    """pandas row -> 'Maurice / Consumables'."""
    line = product_line(row.get("ItemDesc", ""))     # ← was ProductLine (cryptic codes)
    cat = category(row.get("InstConsSvc", ""), row.get("ItemDesc", ""))
    return f"{line} / {cat}"
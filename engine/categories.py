"""Map raw transactions to the CY26 taxonomy: 'ProductLine / Category'."""


# iCE280/iCE3-specific parts/consumables whose descriptions don't contain
# "ice" — confirmed via customer purchase history (overwhelmingly bought by
# iCE3-only customers, unlike genuinely shared items — see
# AMBIGUOUS_SHARED_ITEMS below).
ICE3_SPECIFIC_ITEMS = {
    "electrolyte pipettes",
    "injection needle, alcott",
    "platinum electrode",
}


def product_line(desc: str) -> str:
    """iCE3 / Maurice / MFI — detected from the ItemDesc product name."""
    d = str(desc).lower()
    if "maurice" in d:                       # covers 'Maurice' + 'MauriceFlex'
        return "Maurice"
    if "mfi" in d:
        return "MFI"
    if "ice" in d:                           # covers 'iCE3', 'iCE280', 'iCE System'
        return "iCE3"
    if "fc-coated" in d or "fc and ht cartridge" in d:  # iCE3's FC cartridge line
        return "iCE3"
    if d in ICE3_SPECIFIC_ITEMS:
        return "iCE3"
    return "Other"


# "Cart" = the actual cartridge product (e.g. "cIEF Cartridge, Maurice"), not
# accessories/parts sold alongside cartridges (cleaning vials, inserts,
# sleeves, tools) — those are priced very differently and belong in plain
# Consumables instead.
CARTRIDGE_ACCESSORY_KEYWORDS = ("cleaning", "insert", "sleeve", "tool", "vial", "wash")


def category(inst_cons_svc: str, desc: str = "") -> str:
    """Units / Consumables / Service (+ sub-splits)."""
    s, d = str(inst_cons_svc).lower(), str(desc).lower()

    if "crate" in d:
        return "Other"  # freight/packaging charge, not a real service line
    if "instrument" in s or "unit" in s:
        return "Units"
    if "service" in s:
        return "Service Contracts" if ("contract" in d or "plan" in d) else "Service"
    if "consumable" in s:
        if "cartridge" in d and not any(kw in d for kw in CARTRIDGE_ACCESSORY_KEYWORDS):
            return "Consumables - Cart"
        return "Consumables"
    return "Other"


def classify(row) -> str:
    """pandas row -> 'Maurice / Consumables'."""
    line = product_line(row.get("ItemDesc", ""))     # ← was ProductLine (cryptic codes)
    cat = category(row.get("InstConsSvc", ""), row.get("ItemDesc", ""))
    return f"{line} / {cat}"


# Reagents/consumables sold as a common item across instrument lines — ItemDesc
# alone can't say which instrument a given sale was for.
AMBIGUOUS_SHARED_ITEMS = {"1% Methyl Cellulose Solution"}


def resolve_shared_items(df):
    """Reassign AMBIGUOUS_SHARED_ITEMS rows (currently 'Other / ...') to a real
    product line using the purchasing customer's OTHER purchases: if a
    customer has only ever bought one instrument line, their shared-item
    purchases are attributed to that line. Customers who own multiple lines
    (or show no line signal at all) keep the shared item as 'Other' — those
    sales genuinely can't be attributed to one instrument."""
    is_shared = df["ItemDesc"].isin(AMBIGUOUS_SHARED_ITEMS)
    if not is_shared.any():
        return df

    known = df.loc[~is_shared, ["CustomerNo", "ProdGroup"]]
    known = known[known["ProdGroup"].str.split(" / ").str[0].isin(["Maurice", "iCE3", "MFI"])]
    cust_lines = known.groupby("CustomerNo")["ProdGroup"].apply(
        lambda s: set(x.split(" / ")[0] for x in s)
    )

    def resolve(customer_no, prod_group):
        lines = cust_lines.get(customer_no, set())
        if len(lines) == 1:
            _, _, cat = prod_group.partition(" / ")
            return f"{next(iter(lines))} / {cat}"
        return prod_group

    df.loc[is_shared, "ProdGroup"] = df.loc[is_shared].apply(
        lambda row: resolve(row["CustomerNo"], row["ProdGroup"]), axis=1
    )
    return df


# iCE3 and MFI hardware instruments are discontinued — no new units are sold,
# so that "Units" category shouldn't be priced going forward. Their
# Consumables/Service lines remain active and priceable.
DISCONTINUED_INSTRUMENT_LINES = {"iCE3", "MFI"}


def is_priceable(prod_group: str) -> bool:
    """'Maurice / Units' -> True. Excluded: discontinued instrument lines'
    Units, and Service Contracts for every line (its price change tracks the
    instrument's Units price rather than being modeled independently)."""
    line, _, cat = prod_group.partition(" / ")
    if cat == "Service Contracts":
        return False
    return not (cat == "Units" and line in DISCONTINUED_INSTRUMENT_LINES)
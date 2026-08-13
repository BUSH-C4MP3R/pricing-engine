"""Map raw transactions to the CY26 taxonomy: 'ProductLine / Category'."""

import re

# Matches "ice" only when NOT preceded by a letter — catches "iCE3", "iCE280",
# a standalone "iCE" — but not "serv[ice]", "pr[ice]", "not[ice]", "dev[ice]",
# "tw[ice]", "cho[ice]": a naive "ice" in d substring check would misfire on
# any of those (this dataset is full of "Service"/"Price" mentions).
_ICE_PATTERN = re.compile(r"(?<![a-z])ice")


def _mentions_ice(d: str) -> bool:
    return bool(_ICE_PATTERN.search(d))


# Whole-word "Mau" is an abbreviation for Maurice used on some service items
# (e.g. "Service Visit Tier 1 - Mau", "1 Day Labor - Mau") — word-bounded so
# it doesn't match "mau" as a substring of another word (no false positives
# like "mauve" found in this dataset; "maurice" itself is handled separately).
_MAU_PATTERN = re.compile(r"\bmau\b")


def _mentions_mau(d: str) -> bool:
    return bool(_MAU_PATTERN.search(d))


# iCE280/iCE3-specific parts/consumables whose descriptions don't contain
# "ice" — confirmed via customer purchase history (overwhelmingly bought by
# iCE3-only customers, unlike genuinely shared items — see
# AMBIGUOUS_SHARED_ITEMS below).
ICE3_SPECIFIC_ITEMS = {
    "electrolyte pipettes",
    "injection needle, alcott",
    "platinum electrode",
}


def _maurice_sub_line(d: str, mode: str) -> str:
    """Maurice sub-classification depends on WHAT is being classified, not
    just what the description mentions:
    - Units: instrument variant ('Maurice C.' / 'Maurice S.' / 'Maurice Flex')
      — PM/RQ/IQ-OQ pricing and the instrument itself are tied to a specific
      model. 'OBM' configuration items (e.g. '090-153' "Maurice - OBM",
      '090-154' "Maurice C. - OBM") are grouped back in with their non-OBM
      counterpart ('Maurice' / 'Maurice C.') rather than split out separately.
    - Consumables (+ Cart): chemistry ('Maurice CE-SDS' / 'Maurice icIEF') —
      the same instrument runs either assay, and they show different
      elasticity, but a cartridge/reagent isn't tied to one instrument model.
    - Service / Service Contracts / Other: no sub-split — e.g. "Maurice C.
      IQ/OQ Service" and "Maurice CE-SDS Applications Training" both just
      fold into generic 'Maurice', regardless of the variant/chemistry named.
    `d` is already lowercased and confirmed to contain 'maurice'."""
    if mode == "variant":
        if "mauriceflex" in d:
            return "Maurice Flex"
        if "maurice c." in d:
            return "Maurice C."
        if "maurice s." in d:
            return "Maurice S."
        return "Maurice"
    if mode == "chemistry":
        if "ce-sds" in d:
            return "Maurice CE-SDS"
        if "cief" in d:
            return "Maurice icIEF"
    return "Maurice"


def product_line(desc: str, maurice_mode: str = "none") -> str:
    """iCE3 / Maurice / MFI — detected from the ItemDesc product name.
    `maurice_mode` ('variant' | 'chemistry' | 'none') controls how Maurice
    items get sub-classified — see _maurice_sub_line(). classify() decides
    the mode based on the item's category (Units/Consumables/Service)."""
    d = str(desc).lower()
    if "maurice" in d or _mentions_mau(d):    # covers 'Maurice' + 'MauriceFlex' + abbreviated 'Mau'
        return _maurice_sub_line(d, maurice_mode)
    if maurice_mode == "chemistry" and "ce-sds" in d:
        # CE-SDS chemistry is exclusively Maurice's, even on items missing
        # "maurice" in the name (e.g. "Turbo CE-SDS Running Buffer - Bottom")
        return "Maurice CE-SDS"
    if "obm" in d:                           # 'OBM' is a Maurice-specific configuration term
        return "Maurice"
    if "mfi" in d:
        return "MFI"
    if _mentions_ice(d):                     # covers 'iCE3', 'iCE280', 'iCE System'
        return "iCE3"
    if "fc-coated" in d or "ht-coated" in d or "fc and ht cartridge" in d:  # iCE3's FC/HT cartridge line
        return "iCE3"
    if "cief" in d:                          # iCE280/iCE3 cIEF chemistry items with no "ice"/"maurice" in the name
        return "iCE3"
    if d in ICE3_SPECIFIC_ITEMS:
        return "iCE3"
    return "Other"


# "Cart" = the actual cartridge product (e.g. "cIEF Cartridge, Maurice"), not
# accessories/parts sold alongside cartridges (cleaning vials, inserts,
# sleeves, tools, qualification assemblies) — those are priced very
# differently and belong in plain Consumables instead.
CARTRIDGE_ACCESSORY_KEYWORDS = ("cleaning", "insert", "sleeve", "tool", "vial", "wash", "assy", "assembly")

# The handful of real instrument-system SKUs — exact ItemCode match, since
# bare model names ("Maurice", "Maurice C.", "MauriceFlex", "MFI 5100 Flow
# Microscope System"...) have no distinguishing keyword to key off of, unlike
# every other category here. "090-000-M" (Monthly Usage of Maurice, a
# lease/rental fee) is deliberately excluded — it's not an instrument sale.
UNIT_ITEM_CODES = {
    "090-000", "090-153", "090-155", "090-153-R", "090-000-R",
    "090-002", "090-154", "090-002-R", "090-141", "090-156",
    "090-001", "090-158", "090-139",
    "4000-011-001", "4000-015-001", "P-0000013-00", "P-0000014-00",
    "004-003", "004-001", "004-005", "004-001-R",
}

# Codes for one-off services (PM/RQ/IQ-OQ events, field service labor/travel/
# expense, day-rate labor, service visits, depot service, a one-time upgrade)
# — this dataset has no InstConsSvc field, so ItemCode prefixes are the most
# reliable signal (far more consistent than the free-text descriptions).
SERVICE_CODE_PREFIXES = (
    "pm-", "rq-", "iqoq-", "ssv", "mauremp",
    "s-fld", "s-1day", "s-1/2day", "s-visit", "s-tm-ds", "s-mau-w11",
)

# Non-recurring charges that aren't real product/service revenue at all.
OTHER_KEYWORDS = ("crate", "installation kit", "freight", "trade-in credit")


def category(item_code: str, desc: str = "") -> str:
    """Units / Consumables / Service (+ sub-splits) — classified from
    ItemCode patterns and ItemDesc keywords (this dataset has no InstConsSvc
    field to lean on, unlike the original CSV)."""
    code, d = str(item_code).lower(), str(desc).lower()

    if any(kw in d for kw in OTHER_KEYWORDS):
        return "Other"  # freight/packaging/lease/trade-in — not real product/service revenue

    if item_code in UNIT_ITEM_CODES:
        return "Units"

    # Service Contracts: Silver/Gold/Platinum tiers are embedded right in the
    # ItemCode (e.g. "C-MFI-GOLD", "S-MAURICE-SLVR"), which is more reliable
    # than the description (e.g. "Platinum Electrode" is a hardware part, not
    # a contract — its ItemCode doesn't contain "plat").
    if any(tier in code for tier in ("gold", "silver", "slvr", "plat")):
        return "Service Contracts"
    if code.startswith(("reinstate", "c-")):
        return "Service Contracts"
    if "full coverage" in d and ("service" in d or "plan" in d):
        return "Service Contracts"

    if code.startswith(SERVICE_CODE_PREFIXES):
        return "Service"
    if "iq/oq" in code or "iq/oq" in d:
        return "Service"
    if any(kw in d for kw in (
        "preventive maintenance", "preventative maintenance", "requalification",
        "training", "applications support", "single service visit", "service visit",
        "field service", "day labor", "depot service", "custom development",
        "certification program", "installation and configuration",
        "upgrade and qualification",
    )):
        return "Service"
    if "(service)" in d:
        return "Service"

    if "cartridge" in d and not any(kw in d for kw in CARTRIDGE_ACCESSORY_KEYWORDS):
        return "Consumables - Cart"
    return "Consumables"


MAURICE_MODE_BY_CATEGORY = {
    "Units": "variant",
    "Consumables": "chemistry",
    "Consumables - Cart": "chemistry",
}


def classify(row) -> str:
    """pandas row -> 'Maurice / Consumables'."""
    item_code, desc = row.get("ItemCode", ""), row.get("ItemDesc", "")
    cat = category(item_code, desc)
    mode = MAURICE_MODE_BY_CATEGORY.get(cat, "none")  # Service/Service Contracts/Other: no sub-split
    line = product_line(desc, mode)
    return f"{line} / {cat}"


# Reagents/consumables sold as a common item across instrument lines — ItemDesc
# alone can't say which instrument a given sale was for.
AMBIGUOUS_SHARED_ITEMS = {
    "1% Methyl Cellulose Solution",
    "0.5% Methyl Cellulose Solution (2 x 100mL)",
}


def _base_line(line: str) -> str:
    """'Maurice CE-SDS' / 'Maurice icIEF' -> 'Maurice' — a shared item (like
    the methyl cellulose reagent) can't be attributed to one chemistry, so a
    customer who's only ever bought one sub-chemistry still just counts as a
    'Maurice' customer for this purpose."""
    return "Maurice" if line.startswith("Maurice") else line


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

    known = df.loc[~is_shared, ["CustomerNo", "ProdGroup"]].copy()
    known["Line"] = known["ProdGroup"].str.split(" / ").str[0].map(_base_line)
    known = known[known["Line"].isin(["Maurice", "iCE3", "MFI"])]
    cust_lines = known.groupby("CustomerNo")["Line"].apply(set)

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


# iCE3's hardware instrument is discontinued — no new units are sold, so that
# "Units" category shouldn't be priced going forward, but its Consumables/
# Service lines remain active. MFI is discontinued entirely — omit the whole
# line from pricing.
DISCONTINUED_UNITS_ONLY = {"iCE3"}
FULLY_DISCONTINUED_LINES = {"MFI"}


def is_priceable(prod_group: str) -> bool:
    """'Maurice OBM / Units' -> True. Excluded: MFI entirely (fully discontinued),
    and iCE3's Units specifically (discontinued instrument, Consumables/
    Service/Service Contracts remain active). Service Contracts are priced
    independently now that real Silver/Gold/Platinum plan data exists (see
    the 2,406-row cross-line breakdown that prompted this)."""
    line, _, cat = prod_group.partition(" / ")
    if line in FULLY_DISCONTINUED_LINES:
        return False
    return not (cat == "Units" and line in DISCONTINUED_UNITS_ONLY)
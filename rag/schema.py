## 2. Schema validation (build/test this first)

"""
Validates LLM-extracted data before it reaches the deterministic engine.
This is the safety net that guarantees calculate_price() never receives
malformed input.
"""

REQUIRED_FIELDS = {
    "product": str,
    "current_price": (int, float),
    "inflation": (int, float),
    "cost_change": (int, float),
    "last_price_change": (int, float),
    "volume_change": (int, float),
}


def validate_product(data: dict) -> dict:
    """Raise a clear error if the LLM output is missing or malformed."""
    missing = REQUIRED_FIELDS.keys() - data.keys()
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    for field, expected_type in REQUIRED_FIELDS.items():
        if not isinstance(data[field], expected_type):
            raise TypeError(
                f"Field '{field}' expected {expected_type}, "
                f"got {type(data[field]).__name__}"
            )
    return data
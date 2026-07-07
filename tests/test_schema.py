"""Unit tests for the validation safety net."""

import pytest
from rag.schema import validate_product

VALID = {
    "product": "Biologics-A",
    "current_price": 100.0,
    "inflation": 0.03,
    "cost_change": 0.02,
    "last_price_change": 0.10,
    "volume_change": -0.30,
}


def test_valid_passes():
    assert validate_product(VALID) == VALID


def test_missing_field_raises():
    bad = {k: v for k, v in VALID.items() if k != "inflation"}
    with pytest.raises(ValueError, match="Missing required fields"):
        validate_product(bad)


def test_wrong_type_raises():
    bad = {**VALID, "current_price": "one hundred"}
    with pytest.raises(TypeError):
        validate_product(bad)

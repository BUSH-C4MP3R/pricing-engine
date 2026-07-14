"""Regression tests. Run: python -m pytest tests/test_pipeline.py -v"""

import json
import unittest
from engine.categories import classify
from engine.pricing import calculate_price


class TestClassifier(unittest.TestCase):
    def test_maurice_cart(self):
        self.assertEqual(
            classify({"ItemDesc": "Maurice cIEF Cartridge",
                      "InstConsSvc": "Consumable"}),
            "Maurice / Consumables - Cart")

    def test_ice3_from_desc(self):
        self.assertEqual(
            classify({"ItemDesc": "iCE3 Waste Line",
                      "InstConsSvc": "Consumable"}),
            "iCE3 / Consumables")


class TestOutputIntegrity(unittest.TestCase):
    def setUp(self):
        with open("output/pricing_results.json") as f:
            self.results = json.load(f)

    def test_nine_unique_products(self):
        names = [r["product"] for r in self.results]
        self.assertEqual(len(names), len(set(names)), f"Dupes: {names}")

    def test_pricing_is_additive(self):
        for r in self.results:
            expected = r["current_price"] * (1 + r["total_adj"])
            tolerance = r["current_price"] * 0.001          # ← allow total_adj rounding
            self.assertAlmostEqual(r["final_price"], expected, delta=tolerance,
                                   msg=f"{r['product']} not additive")


if __name__ == "__main__":
    unittest.main(verbosity=2)
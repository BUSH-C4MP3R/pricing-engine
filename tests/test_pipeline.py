"""Regression tests. Run: python -m pytest tests/test_pipeline.py -v"""

import json
import unittest
from engine.categories import classify, is_priceable
from engine.pricing import calculate_price


class TestClassifier(unittest.TestCase):
    def test_maurice_cart(self):
        self.assertEqual(
            classify({"ItemCode": "090-101", "ItemDesc": "Maurice cIEF Cartridge"}),
            "Maurice icIEF / Consumables - Cart")

    def test_maurice_generic_consumable_stays_unsplit(self):
        self.assertEqual(
            classify({"ItemCode": "046-017", "ItemDesc": "Maurice Glass Reagent Vials, 2 mL"}),
            "Maurice / Consumables")

    def test_ice3_from_desc(self):
        self.assertEqual(
            classify({"ItemCode": "045-089", "ItemDesc": "iCE3 Waste Line"}),
            "iCE3 / Consumables")

    def test_service_does_not_false_positive_as_ice3(self):
        # "Service" contains the substring "ice" (serv-ICE) — a naive "ice" in
        # d check would misclassify any generic service item as iCE3.
        self.assertEqual(
            classify({"ItemCode": "S-TM-DS", "ItemDesc": "Time & Materials Depot Service"}),
            "Other / Service")
        self.assertEqual(
            classify({"ItemCode": "S-VISITT1-ICE", "ItemDesc": "Service Visit Tier 1 - iCE"}),
            "iCE3 / Service")

    def test_mau_abbreviation_is_maurice(self):
        self.assertEqual(
            classify({"ItemCode": "S-VisitT1-Mau", "ItemDesc": "Service Visit Tier 1 - Mau"}),
            "Maurice / Service")

    def test_unit_item_code(self):
        self.assertEqual(
            classify({"ItemCode": "090-002", "ItemDesc": "Maurice C."}),
            "Maurice C. / Units")

    def test_service_contract_tier_in_code(self):
        self.assertEqual(
            classify({"ItemCode": "C-MFI-GOLD", "ItemDesc": "MFI Gold Service Plan"}),
            "MFI / Service Contracts")

    def test_service_contract_tier_does_not_match_hardware_part(self):
        # "Platinum Electrode" is a hardware part, not a contract — its
        # ItemCode (unlike a real contract SKU) doesn't contain "plat".
        self.assertEqual(
            classify({"ItemCode": "101454", "ItemDesc": "Platinum Electrode"}),
            "iCE3 / Consumables")

    def test_preventive_maintenance_is_service(self):
        self.assertEqual(
            classify({"ItemCode": "PM-Maurice", "ItemDesc": "Maurice PM"}),
            "Maurice / Service")

    def test_pm_kit_is_consumable_not_service(self):
        # A physical parts kit, not the PM labor event itself.
        self.assertEqual(
            classify({"ItemCode": "104-0008", "ItemDesc": "PM Kit, Maurice C"}),
            "Maurice / Consumables")

    def test_crate_excluded(self):
        self.assertEqual(
            classify({"ItemCode": "102-0004", "ItemDesc": "Crate Maurice"}),
            "Maurice / Other")

    def test_consumables_split_by_chemistry_not_variant(self):
        # Even though this cartridge names the Flex variant, Consumables are
        # split by chemistry only — variant splitting is for Units.
        self.assertEqual(
            classify({"ItemCode": "PS-MC02-F",
                      "ItemDesc": "MauriceFlex cIEF Fractionation Cartridge - 2pk"}),
            "Maurice icIEF / Consumables - Cart")

    def test_service_collapses_to_generic_maurice(self):
        # Service isn't split by variant or chemistry, unlike Units/Consumables.
        self.assertEqual(
            classify({"ItemCode": "MAURICE C IQ/OQ", "ItemDesc": "Maurice C. IQ/OQ Service"}),
            "Maurice / Service")
        self.assertEqual(
            classify({"ItemCode": "PS-T014", "ItemDesc": "Maurice CE-SDS Applications Training"}),
            "Maurice / Service")

    def test_mfi_fully_excluded_from_pricing(self):
        for cat in ("Units", "Consumables", "Service", "Service Contracts"):
            self.assertFalse(is_priceable(f"MFI / {cat}"), f"MFI / {cat} should be excluded")

    def test_ice3_only_units_excluded(self):
        self.assertFalse(is_priceable("iCE3 / Units"))
        self.assertTrue(is_priceable("iCE3 / Consumables"))

    def test_service_contracts_priceable_except_mfi(self):
        self.assertTrue(is_priceable("Maurice / Service Contracts"))
        self.assertTrue(is_priceable("iCE3 / Service Contracts"))
        self.assertFalse(is_priceable("MFI / Service Contracts"))


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
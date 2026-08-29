from __future__ import annotations

import unittest

from analysis.coverage_stress import FieldMaskPlan, apply_masks_to_product, plan_field_masks


class CoverageStressPlanTest(unittest.TestCase):
    def setUp(self) -> None:
        self.products = [
            {
                "parent_asin": "A",
                "price": 10.0,
                "features": ["cotton"],
                "description": ["alpha"],
                "details": {"color": "red"},
                "store": "one",
            },
            {
                "parent_asin": "B",
                "price": 20.0,
                "features": ["wool"],
                "description": [],
                "details": {"color": "blue"},
                "store": "two",
            },
            {
                "parent_asin": "C",
                "price": None,
                "features": ["silk"],
                "description": ["charlie"],
                "details": {},
                "store": None,
            },
            {
                "parent_asin": "D",
                "price": None,
                "features": [],
                "description": ["delta"],
                "details": {"color": "black"},
                "store": "four",
            },
        ]

    def test_plan_masks_only_overcovered_target_fields(self) -> None:
        plans = plan_field_masks(
            self.products,
            target_ids=("A", "B"),
            fields=("price", "features", "description", "details", "store"),
            seed="fixed",
        )

        self.assertEqual(1, plans["price"].desired_target_present)
        self.assertEqual(2, plans["price"].original_target_present)
        self.assertEqual(1, len(plans["price"].masked_ids))
        self.assertEqual(frozenset({"A"}), plans["price"].masked_ids)
        self.assertEqual(2, plans["description"].desired_target_present)
        self.assertEqual(1, plans["description"].original_target_present)
        self.assertEqual(0, len(plans["description"].masked_ids))
        self.assertEqual(1, plans["description"].unfillable_shortfall)

    def test_apply_masks_never_fills_a_missing_field(self) -> None:
        plans = plan_field_masks(
            self.products,
            target_ids=("A", "B"),
            fields=("price", "description"),
            seed="fixed",
        )
        masked = [apply_masks_to_product(product, plans) for product in self.products]

        self.assertEqual([], masked[1]["description"])
        self.assertEqual(["charlie"], masked[2]["description"])
        self.assertEqual(["delta"], masked[3]["description"])
        self.assertEqual(1, sum(row["price"] is not None for row in masked[:2]))

        details_plan = FieldMaskPlan(
            field="details",
            catalog_present=4,
            catalog_coverage=1.0,
            desired_target_present=1,
            original_target_present=1,
            masked_ids=frozenset({"A"}),
            unfillable_shortfall=0,
        )
        self.assertEqual({}, apply_masks_to_product(self.products[0], {"details": details_plan})["details"])

    def test_same_seed_produces_the_same_mask_ids(self) -> None:
        first = plan_field_masks(self.products, ("A", "B"), ("price",), "fixed")
        second = plan_field_masks(self.products, ("B", "A"), ("price",), "fixed")
        self.assertEqual(first["price"].masked_ids, second["price"].masked_ids)

    def test_rejects_duplicate_target_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be distinct"):
            plan_field_masks(self.products, ("A", "A"), ("price",), "fixed")

    def test_rejects_missing_target_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing from catalog"):
            plan_field_masks(self.products, ("A", "missing"), ("price",), "fixed")

    def test_rejects_duplicate_catalog_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate catalog parent_asin"):
            plan_field_masks([self.products[0], self.products[0]], ("A",), ("price",), "fixed")


if __name__ == "__main__":
    unittest.main()

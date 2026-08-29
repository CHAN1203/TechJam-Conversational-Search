from __future__ import annotations

import unittest

from analysis.gazetteer import (
    build_attribute_seeds,
    build_category_gazetteer,
    build_gazetteer,
    is_usable_term,
    measure_term_coverage,
    resolve_slot_conflicts,
    normalize_department,
    normalize_term,
)


class NormalizeDepartmentTest(unittest.TestCase):
    def test_normalizes_surface_variants_to_canonical_departments(self) -> None:
        cases = {
            "womens": "women",
            "Women": "women",
            "women's": "women",
            "ladies": "women",
            "mens": "men",
            "MEN": "men",
            "men's": "men",
            "adult-male": "men",
            "girls": "girls",
            "baby-girls": "girls",
            "teen-girls": "girls",
            "boys": "boys",
            "baby boys": "boys",
            "unisex-adult": "unisex-adult",
            "unisex adult": "unisex-adult",
            "unisex": "unisex-adult",
            "unisex-adult (luggage only)": "unisex-adult",
            "unisex-child": "unisex-child",
            "kids": "unisex-child",
            "unisex-baby": "unisex-child",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_department(raw), expected)

    def test_returns_none_for_unmapped_or_empty_values(self) -> None:
        for raw in ("luggage", "", "   ", None, "wristwatch"):
            with self.subTest(raw=raw):
                self.assertIsNone(normalize_department(raw))


if __name__ == "__main__":
    unittest.main()


class NormalizeTermTest(unittest.TestCase):
    def test_lowercases_strips_punctuation_and_singularizes_head_tokens(self) -> None:
        cases = {
            "T-Shirts": "t shirt",
            "Shoes": "shoe",
            "Scarves": "scarf",
            "Clutches": "clutch",
            "Booties": "bootie",
            "Watches": "watch",
            "Boxes": "box",
            "Accessories": "accessory",
            "Hoodies": "hoodie",
            "Neckties": "necktie",
            "Blouses": "blouse",
            "Dresses": "dress",
            "Sunglasses": "sunglass",
            "Gloves": "glove",
            "Road Running": "road running",
            "Dress": "dress",
            "  Jackets & Coats  ": "jacket & coat",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_term(raw), expected)


class CategoryGazetteerTest(unittest.TestCase):
    ROOT = "Clothing, Shoes & Jewelry"

    def test_keeps_only_nodes_attested_below_the_department_level(self) -> None:
        products = [
            {"categories": [self.ROOT, "Women", "Shoes", "Athletic", "Road Running"]},
            {"categories": [self.ROOT, "Westlake"]},
            {"categories": [self.ROOT, "Men", "Shirts", "T-Shirts"]},
            {"categories": [self.ROOT, "Men", "Shoes", "Boots"]},
        ]
        self.assertEqual(
            build_category_gazetteer(products),
            {
                "shoe": 2,
                "athletic": 1,
                "road running": 1,
                "shirt": 1,
                "t shirt": 1,
                "boot": 1,
            },
        )

    def test_splits_compound_nodes_into_separately_matchable_terms(self) -> None:
        products = [
            {"categories": [self.ROOT, "Women", "Clothing", "Tops, Tees & Blouses"]},
            {"categories": [self.ROOT, "Women", "Accessories", "Skullies & Beanies"]},
            {"categories": [self.ROOT, "Men", "Clothing", "Jackets and Coats"]},
        ]
        gazetteer = build_category_gazetteer(products)
        for term in ("top", "tee", "blouse", "skullie", "beanie", "jacket", "coat"):
            with self.subTest(term=term):
                self.assertIn(term, gazetteer)
        self.assertNotIn("top tee & blouse", gazetteer)

    def test_ignores_products_without_categories(self) -> None:
        products = [{"categories": None}, {"categories": []}, {}]
        self.assertEqual(build_category_gazetteer(products), {})


class AttributeSeedTest(unittest.TestCase):
    def test_mines_seed_vocabulary_from_a_sparse_detail_key(self) -> None:
        products = [
            {"details": {"Material": "Leather"}},
            {"details": {"Material": "polyester, cotton"}},
            {"details": {"Material": "Faux Leather", "Color": "Black"}},
            {"details": {"Color": "Black/White"}},
            {"details": {}},
            {},
        ]
        self.assertEqual(
            build_attribute_seeds(products, "Material"),
            {"leather": 1, "polyester": 1, "cotton": 1, "faux leather": 1},
        )
        self.assertEqual(
            build_attribute_seeds(products, "Color"),
            {"black": 2, "white": 1},
        )


class TermCoverageTest(unittest.TestCase):
    def test_counts_items_whose_text_contains_each_term(self) -> None:
        products = [
            {"title": "Mens Leather Boot", "features": ["waterproof"]},
            {"title": "Cotton Tee", "features": ["soft leather trim"]},
            {"title": "Nylon Jacket", "features": []},
        ]
        self.assertEqual(
            measure_term_coverage(products, ("leather", "cotton", "silk")),
            {"leather": 2, "cotton": 1, "silk": 0},
        )

    def test_matches_on_whole_words_not_substrings(self) -> None:
        products = [{"title": "Cottonwood Print Scarf", "features": []}]
        self.assertEqual(
            measure_term_coverage(products, ("cotton",)),
            {"cotton": 0},
        )


class BuildGazetteerTest(unittest.TestCase):
    ROOT = "Clothing, Shoes & Jewelry"

    def _products(self) -> list[dict]:
        return [
            {
                "title": "Mens Leather Boot",
                "features": ["waterproof"],
                "categories": [self.ROOT, "Men", "Shoes", "Boots"],
                "details": {"Department": "mens", "Material": "Leather"},
            },
            {
                "title": "Womens Cotton Dress",
                "features": ["black"],
                "categories": [self.ROOT, "Women", "Clothing", "Dresses"],
                "details": {"Department": "womens", "Material": "Cotton", "Color": "Black"},
            },
        ]

    def test_assembles_every_slot_keyed_by_free_text_support(self) -> None:
        gazetteer = build_gazetteer(self._products())
        self.assertEqual(sorted(gazetteer), ["category", "color", "department", "material", "size", "style"])
        self.assertEqual(gazetteer["department"], {"men": 1, "women": 1})
        self.assertEqual(gazetteer["material"], {"leather": 1, "cotton": 1})
        self.assertEqual(gazetteer["color"], {"black": 1})
        self.assertIn("boot", gazetteer["category"])
        self.assertIn("dress", gazetteer["category"])

    def test_output_never_files_a_term_under_two_slots(self) -> None:
        products = [
            {
                "title": "Cotton Wrap",
                "features": ["soft cotton"],
                "categories": [self.ROOT, "Women", "Clothing", "Cotton"],
                "details": {"Department": "womens", "Material": "Cotton"},
            },
        ]
        gazetteer = build_gazetteer(products)
        owners = {}
        for slot, terms in gazetteer.items():
            for term in terms:
                owners.setdefault(term, []).append(slot)
        self.assertEqual([t for t, s in owners.items() if len(s) > 1], [])
        self.assertIn("cotton", gazetteer["material"])
        self.assertNotIn("cotton", gazetteer["category"])

    def test_drops_attribute_terms_with_no_free_text_support(self) -> None:
        products = self._products()
        products[0]["details"]["Material"] = "Unobtanium"
        gazetteer = build_gazetteer(products)
        self.assertNotIn("unobtanium", gazetteer["material"])


class GazetteerTermFilterTest(unittest.TestCase):
    def test_rejects_terms_without_a_discriminating_word(self) -> None:
        for term in ("a", "1", "5", "10", "x", "", "  ", "8 5"):
            with self.subTest(term=term):
                self.assertFalse(is_usable_term(term))

    def test_accepts_terms_with_a_real_word(self) -> None:
        for term in ("black", "one size", "8 inch", "x large", "faux leather"):
            with self.subTest(term=term):
                self.assertTrue(is_usable_term(term))


class SlotConflictTest(unittest.TestCase):
    def test_assigns_each_term_to_exactly_one_slot_by_precedence(self) -> None:
        gazetteer = {
            "department": {"women": 25792},
            "category": {"women": 3029, "hoodie": 268, "cotton": 28, "boot": 900},
            "material": {"cotton": 9402, "silver": 2935},
            "style": {"hoodie": 1169, "casual": 7487},
            "color": {"silver": 2935, "small": 2942},
            "size": {"small": 2942},
        }
        self.assertEqual(
            resolve_slot_conflicts(gazetteer),
            {
                "department": {"women": 25792},
                "material": {"cotton": 9402, "silver": 2935},
                "size": {"small": 2942},
                "category": {"hoodie": 268, "boot": 900},
                "color": {},
                "style": {"casual": 7487},
            },
        )

    def test_leaves_an_uncontaminated_gazetteer_unchanged(self) -> None:
        gazetteer = {
            "category": {"boot": 900},
            "material": {"cotton": 9402},
        }
        self.assertEqual(resolve_slot_conflicts(gazetteer), gazetteer)

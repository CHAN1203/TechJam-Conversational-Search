from __future__ import annotations

import unittest

from analysis.catalog_profile import profile_catalog


class CatalogProfileTest(unittest.TestCase):
    def test_profile_catalog_counts_empty_collections_as_missing(self) -> None:
        products = [
            {"title": "Shoe", "features": ["leather"], "details": {}},
            {"title": "Boot", "features": [], "details": {"color": "black"}},
            {"title": "", "features": None, "details": None},
        ]
        self.assertEqual(
            profile_catalog(products, ("title", "features", "details")),
            {
                "row_count": 3,
                "fields": {
                    "details": {
                        "present": 1,
                        "missing": 2,
                        "coverage": 0.333333,
                    },
                    "features": {
                        "present": 1,
                        "missing": 2,
                        "coverage": 0.333333,
                    },
                    "title": {
                        "present": 2,
                        "missing": 1,
                        "coverage": 0.666667,
                    },
                },
            },
        )


if __name__ == "__main__":
    unittest.main()

"""Synthetic-only EST-001 taxonomy tests; every example is invented."""

from dataclasses import FrozenInstanceError, fields
import unittest

from estimator.taxonomy import (
    FINISH_TYPES, SHEENS, SCOPE_CATEGORIES, TAXONOMY_VERSION,
    FinishRequirement, PaintingScope,
)


class PaintingTaxonomyTests(unittest.TestCase):
    def test_versioned_stable_identifiers_and_supported_categories(self):
        self.assertEqual(TAXONOMY_VERSION, "painting-takeoff/v1")
        self.assertEqual(SCOPE_CATEGORIES,
                         ("walls", "ceilings", "doors", "trim", "cabinets", "exterior"))
        self.assertEqual(FINISH_TYPES, ("paint", "stain", "clear_coat"))
        self.assertEqual(SHEENS,
                         ("flat", "matte", "eggshell", "satin", "semi_gloss", "gloss"))
        for category in SCOPE_CATEGORIES:
            with self.subTest(category=category):
                self.assertEqual(PaintingScope(category).category, category)
                self.assertIsNone(PaintingScope(category).finish)

    def test_explicit_finish_intent_not_quantity_or_cost(self):
        for finish_type in FINISH_TYPES:
            for sheen in (*SHEENS, None):
                with self.subTest(finish_type=finish_type, sheen=sheen):
                    finish = FinishRequirement(finish_type, sheen)
                    scope = PaintingScope("cabinets", finish)
                    self.assertEqual(scope.finish, finish)
                    self.assertEqual(scope.finish.sheen, sheen)
        self.assertEqual(tuple(field.name for field in fields(PaintingScope)),
                         ("category", "finish"))
        self.assertEqual(tuple(field.name for field in fields(FinishRequirement)),
                         ("finish_type", "sheen"))
        with self.assertRaises(FrozenInstanceError):
            PaintingScope("walls").category = "doors"
        with self.assertRaises(FrozenInstanceError):
            FinishRequirement("paint").sheen = "gloss"

    def test_invalid_and_unsupported_values_fail_closed(self):
        for value in ("", "wall", "interior", "floors", "WALLS", None, 1, [], True):
            with self.subTest(category=value), self.assertRaises(ValueError):
                PaintingScope(value)
        for value in ("", "primer", "PAINT", None, 1, [], True):
            with self.subTest(finish_type=value), self.assertRaises(ValueError):
                FinishRequirement(value)
        for value in ("", "high_gloss", "Satin", 1, [], True):
            with self.subTest(sheen=value), self.assertRaises(ValueError):
                FinishRequirement("paint", value)
        for value in ("paint", {"finish_type": "paint"}, 1, False, []):
            with self.subTest(finish=value), self.assertRaises(ValueError):
                PaintingScope("walls", value)


if __name__ == "__main__":
    unittest.main()

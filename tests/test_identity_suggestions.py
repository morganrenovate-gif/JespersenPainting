"""Synthetic-only TIME-002 tests. All labels/references below are invented."""

import unittest

from identity.suggestions import IdentityLabel, normalize, suggest


def item(namespace, reference, label):
    return IdentityLabel(namespace, reference, label)


class IdentitySuggestionTests(unittest.TestCase):
    def test_employee_spacing_case_and_job_spelling_are_review_only(self):
        employee = suggest(item("employee", "synthetic-input-e", "  mira   veld  "), (
            item("employee", "synthetic-e1", "Mira Veld"),
        ))
        self.assertEqual(normalize("\tMIRA   VELD\t"), "mira veld")
        self.assertEqual((employee.state, employee.reason), ("needs_review", "normalized_equal"))
        self.assertEqual(employee.candidates[0].normalized_label, "mira veld")
        self.assertEqual(employee.candidates[0].reference, "synthetic-e1")
        job = suggest(item("job", "synthetic-input-j", "Amber Hanger"), (
            item("job", "synthetic-j1", "Amber Hangar"),
        ))
        self.assertEqual((job.state, job.reason), ("needs_review", "single_typo"))
        self.assertEqual(job.candidates[0].normalized_label, "amber hangar")
        self.assertEqual(job.candidates[0].reason, "single_typo")
        spaced_job = suggest(item("job", "synthetic-input-2", "Amber\tHangar"), (
            item("job", "synthetic-j2", "amber hangar"),))
        self.assertEqual((spaced_job.state, spaced_job.reason), ("needs_review", "normalized_equal"))
        swapped = suggest(item("employee", "synthetic-input-3", "Luma Harobr"), (
            item("employee", "synthetic-e3", "Luma Harbor"),))
        self.assertEqual(swapped.reason, "single_typo")

    def test_ambiguous_typo_has_all_candidates_in_reference_order(self):
        source = item("employee", "synthetic-input", "Luma Harbor")
        candidates = (item("employee", "synthetic-z", "Luma Harbors"),
                      item("employee", "synthetic-a", "Luma Harber"))
        result = suggest(source, candidates)
        self.assertEqual((result.state, result.reason), ("needs_review", "ambiguous_typo"))
        self.assertEqual(tuple(c.reference for c in result.candidates), ("synthetic-a", "synthetic-z"))
        self.assertEqual(result, suggest(source, tuple(reversed(candidates))))

    def test_insufficient_and_unsupported_evidence(self):
        self.assertEqual(suggest(item("job", "synthetic-input", "Hangar"), (
            item("job", "synthetic-j", "Hangars"),)).reason, "insufficient_label")
        for source, target in (("Blue Bay", "Blue Day"), ("Bay Dock", "Bays Dock"),
                               ("North Yard 7", "North Yard 8"), ("Amber Hangar", "Azure Hangar")):
            with self.subTest(source=source):
                result = suggest(item("job", "synthetic-input", source),
                                 (item("job", "synthetic-j", target),))
                self.assertEqual((result.state, result.reason, result.candidates),
                                 ("no_suggestion", "no_supported_match", ()))

    def test_collisions_fail_closed(self):
        source = item("employee", "synthetic-input", "Mira Veld")
        result = suggest(source, (item("employee", "synthetic-b", "mira  veld"),
                                  item("employee", "synthetic-a", "MIRA VELD")))
        self.assertEqual((result.state, result.reason), ("needs_review", "normalized_collision"))
        self.assertEqual(tuple(c.reference for c in result.candidates), ("synthetic-a", "synthetic-b"))
        with self.assertRaises(ValueError):
            suggest(source, (item("employee", "synthetic-a", "Mira Veld"),
                             item("employee", "synthetic-a", "Mira Other")))
        with self.assertRaises(ValueError):
            suggest(source, (item("employee", "synthetic-input", "Mira Veld"),))

    def test_namespaces_never_cross_and_no_confirmation_field(self):
        source = item("employee", "synthetic-input", "Amber Hangar")
        result = suggest(source, (item("job", "synthetic-input", "Amber Hangar"),))
        self.assertEqual((result.state, result.reason, result.candidates),
                         ("no_suggestion", "no_supported_match", ()))
        self.assertEqual(suggest(item("job", "synthetic-job", "Mira Veld"),
                                 (item("employee", "synthetic-e", "Mira Veld"),)).candidates, ())
        self.assertFalse(hasattr(result, "confirmed"))
        self.assertFalse(hasattr(result, "mapping"))

    def test_invalid_inputs_fail_without_candidate_output(self):
        for bad in ("", "  ", "Mira-Veld", "Mira\nVeld", "Míra Veld", "Mira_Veld", "Mira 3!", 123):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                item("employee", "synthetic-e", bad)
        with self.assertRaises(ValueError):
            item("person", "synthetic-e", "Mira Veld")
        with self.assertRaises(ValueError):
            item("employee", " ", "Mira Veld")
        with self.assertRaises(ValueError):
            suggest(item("employee", "synthetic-e", "Mira Veld"), [item("employee", "synthetic-c", "Mira Veld")])
        with self.assertRaises(ValueError):
            suggest(item("employee", "synthetic-e", "Mira Veld"), (None,))


if __name__ == "__main__":
    unittest.main()

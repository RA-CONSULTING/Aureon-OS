import unittest
from twig_reader import interpret


def mark(left, right, **changes):
    rec = dict(id="synthetic-test", left_counts=left, right_counts=right,
               alphabet="medieval_16", group_side="left", group_order="reverse",
               provenance={"kind": "synthetic_test_not_observation"})
    rec.update(changes)
    return rec


class ReaderTests(unittest.TestCase):
    def test_barnes_middle_group_example(self):
        self.assertEqual(interpret(mark([2], [1]))["candidates"][0]["transliteration"], "h")

    def test_reverse_numbering_distinguishes_old_mapping(self):
        self.assertEqual(interpret(mark([3], [1]))["candidates"][0]["transliteration"], "f")
        self.assertEqual(interpret(mark([1], [1]))["candidates"][0]["transliteration"], "t")

    def test_unequal_group_limits(self):
        self.assertEqual(interpret(mark([3], [6]))["candidates"][0]["transliteration"], "k")
        for g in [1, 2]:
            self.assertEqual(interpret(mark([g], [6]))["status"], "NO_MATCH_UNDER_DECLARED_CONVENTION")
        self.assertEqual(interpret(mark([3], [8]))["candidates"], [])

    def test_explicit_forward_convention(self):
        self.assertEqual(interpret(mark([1], [1], group_order="forward"))["candidates"][0]["transliteration"], "f")

    def test_orientation_never_silently_swapped(self):
        self.assertEqual(interpret(mark([6], [3]))["candidates"], [])
        self.assertEqual(interpret(mark([6], [3], group_side="right"))["candidates"][0]["transliteration"], "k")

    def test_unknown_remains_unobserved(self):
        self.assertEqual(interpret(mark(None, [1]))["status"], "UNOBSERVED_COUNTS")

    def test_invalid_alternative_preserves_uncertainty(self):
        output = interpret(mark([2], [5, 6]))
        self.assertEqual(output["status"], "AMBIGUOUS_COUNTS")
        self.assertEqual(output["candidates"][0]["transliteration"], "s")
        self.assertEqual(output["rejected_count_pairs"], [{"left": 2, "right": 6}])

    def test_multiple_readings_retained_without_ranking(self):
        output = interpret(mark([1, 3], [2]))
        self.assertEqual([r["transliteration"] for r in output["candidates"]], ["b", "u"])
        self.assertFalse(output["physical_reading_verified"])

    def test_too_many_branches_not_forced_to_fit(self):
        self.assertEqual(interpret(mark([5], [2]))["candidates"], [])
        self.assertEqual(interpret(mark([5], [7]))["candidates"], [])

    def test_bad_count_types_rejected(self):
        for bad in [[True], [1.0], ["1"], [-1], [33], [], [1, 1], "1"]:
            with self.assertRaises(ValueError):
                interpret(mark(bad, [1]))

    def test_missing_direction_and_extra_fields_rejected(self):
        for changes in [{"group_side": None}, {"group_order": None}, {"target_gamma": .945}]:
            with self.assertRaises(ValueError):
                interpret(mark([1], [1], **changes))

    def test_legacy_preset_is_explicit_and_separate(self):
        output = interpret(mark([3], [1], alphabet="elder_24_comparison", group_order="forward"))
        self.assertEqual(output["candidates"][0]["transliteration"], "t")
        self.assertEqual(output["alphabet"], "elder_24_comparison")
        self.assertFalse(output["physical_reading_verified"])


if __name__ == "__main__":
    unittest.main()

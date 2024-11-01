import unittest
from TM1py.Utils.Utils import CaseAndSpaceInsensitiveSet


class TestCaseAndSpaceInsensitiveSet(unittest.TestCase):

    def setUp(self):
        self.original_values = ("Value1", "Value 2", "V A L U E 3")
        self.set = CaseAndSpaceInsensitiveSet()
        for value in self.original_values:
            self.set.add(value)

    def tearDown(self):
        del self.set

    def test_contains(self):
        # Case and space insensitivity
        self.assertIn("Value1", self.set)
        self.assertIn("VALUE1", self.set)
        self.assertIn("V ALUE 1", self.set)
        self.assertIn("Value 2", self.set)
        self.assertIn("V A L UE 2", self.set)
        self.assertIn("VALUE3", self.set)
        self.assertIn("V A LUE 3", self.set)

        # Non-existent values
        self.assertNotIn("Value", self.set)
        self.assertNotIn("VALUE4", self.set)
        self.assertNotIn("VA LUE 4", self.set)

    def test_del(self):
        # Remove elements with del
        del self.set["VALUE1"]
        del self.set["value 2"]
        del self.set["V a L u E 3"]
        # Verify the set is empty
        self.assertFalse(self.set)

    def test_discard(self):
        # Discard elements and check if set is empty
        self.set.discard("Value1")
        self.set.discard("Value 2")
        self.set.discard("Value3")
        self.assertFalse(self.set)

    def test_discard_case_and_space_insensitivity(self):
        # Discard with case and space insensitivity
        self.set.discard("VAL UE 1")
        self.set.discard("Value 2")
        self.set.discard("VA   LUE3")
        self.assertFalse(self.set)

    def test_len(self):
        # Check length after addition and removal
        self.assertEqual(len(self.set), 3)
        self.set.add("Value4")
        self.assertEqual(len(self.set), 4)
        self.set.discard("VALUE4")
        self.assertEqual(len(self.set), 3)

    def test_iter(self):
        # Ensure set iteration matches the original values
        self.assertEqual(len(self.set), len(self.original_values))
        for value in self.set:
            self.assertIn(value, self.original_values)

    def test_add(self):
        # Test adding a new element with various case/space combinations
        self.set.add("Value4")
        self.assertIn("Value4", self.set)
        self.assertIn("VALUE4", self.set)
        self.assertIn(" VALUE4", self.set)
        self.assertIn("VALUE4 ", self.set)
        self.assertIn("V ALUE 4", self.set)
        self.assertIn("Va L UE4", self.set)
        self.assertIn(" VAlue4", self.set)

    def test_copy(self):
        # Verify copy creates a new instance with identical elements
        copy_set = self.set.copy()
        self.assertIsNot(copy_set, self.set)
        self.assertEqual(copy_set, self.set)

    def test_eq(self):
        # Equality with exact and case-insensitive values
        new_set = CaseAndSpaceInsensitiveSet(self.original_values)
        self.assertEqual(self.set, new_set)

        # Case and space-insensitive match
        new_set = CaseAndSpaceInsensitiveSet(value.upper() for value in self.original_values)
        self.assertEqual(self.set, new_set)

    def test_eq_against_builtin_set(self):
        # Equality check against Python's built-in set
        new_set = set(self.original_values)
        self.assertEqual(self.set, new_set)

    def test_ne(self):
        # Inequality with completely different values
        new_set = CaseAndSpaceInsensitiveSet(["wrong1", "wrong2", "wrong3"])
        self.assertNotEqual(self.set, new_set)

    def test_clear(self):
        # Clear the set and verify it's empty
        self.set.clear()
        self.assertEqual(len(self.set), 0)
        self.assertFalse(self.set)

    def test_pop(self):
        # Pop elements and confirm they exist in the original values
        popped_value = self.set.pop()
        self.assertIn(popped_value, self.original_values)
        self.assertEqual(len(self.set), 2)

    def test_update(self):
        # Update set with additional elements
        self.set.update(["NewValue", "Value1"])  # Value1 already exists
        self.assertIn("NewValue", self.set)
        self.assertEqual(len(self.set), 4)

    def test_union(self):
        # Union with another set
        new_set = CaseAndSpaceInsensitiveSet(["ExtraValue", "VALUE1"])
        result_set = self.set.union(new_set)
        self.assertIn("ExtraValue", result_set)
        self.assertEqual(len(result_set), 4)

    def test_intersection(self):
        # Intersection with a set containing common elements
        new_set = CaseAndSpaceInsensitiveSet(["VALUE1", "UnknownValue"])
        result_set = self.set.intersection(new_set)
        self.assertIn("Value1", result_set)
        self.assertEqual(len(result_set), 1)

    def test_difference(self):
        # Difference with another set
        new_set = CaseAndSpaceInsensitiveSet(["Value1", "ExtraValue"])
        result_set = self.set.difference(new_set)
        self.assertNotIn("Value1", result_set)
        self.assertIn("Value 2", result_set)
        self.assertEqual(len(result_set), 2)

    def test_subset_and_superset_operations(self):
        # Test subset, superset, and proper subset/superset relationships
        new_set = CaseAndSpaceInsensitiveSet(["Value1"])
        self.assertTrue(new_set < self.set)  # Proper subset
        self.assertTrue(new_set <= self.set)  # Subset
        self.assertTrue(self.set > new_set)  # Proper superset
        self.assertTrue(self.set >= new_set)  # Superset
        self.assertFalse(new_set > self.set)  # Not a superset
        self.assertFalse(new_set == self.set)  # Not equal

    def test_disjoint(self):
        # Check for disjoint sets
        disjoint_set = CaseAndSpaceInsensitiveSet(["OtherValue"])
        self.assertTrue(self.set.isdisjoint(disjoint_set))

        overlapping_set = CaseAndSpaceInsensitiveSet(["VALUE1", "NewValue"])
        self.assertFalse(self.set.isdisjoint(overlapping_set))


if __name__ == '__main__':
    unittest.main()

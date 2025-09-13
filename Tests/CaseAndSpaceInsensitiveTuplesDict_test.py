import unittest

from TM1py.Utils.Utils import CaseAndSpaceInsensitiveTuplesDict


class TestCaseAndSpaceInsensitiveTuplesDict(unittest.TestCase):

    def setUp(self):
        self.map = CaseAndSpaceInsensitiveTuplesDict()
        self.map[("Elem1", "Elem1")] = "Value1"
        self.map[("Elem1", "Elem2")] = 2
        self.map[("Elem1", "Elem3")] = 3

    def tearDown(self):
        del self.map

    def test_delete_item(self):
        # Verify items exist
        self.assertIn(("Elem1", "Elem1"), self.map)
        self.assertIn(("Elem1", "Elem2"), self.map)
        self.assertIn(("Elem1", "Elem3"), self.map)

        # Delete items with case and space insensitivity
        del self.map[("El em1", "ELEM1")]
        del self.map[("El em1", "E L E M 2")]
        del self.map[("El em1", " eLEM3")]

        # Confirm deletion
        self.assertNotIn(("Elem1", "Elem1"), self.map)
        self.assertNotIn(("Elem1", "Elem2"), self.map)
        self.assertNotIn(("Elem1", "Elem3"), self.map)

    def test_equality(self):
        # Exact match
        other_map = CaseAndSpaceInsensitiveTuplesDict(
            {("Elem1", "Elem1"): "Value1", ("Elem1", "Elem2"): 2, ("Elem1", "Elem3"): 3}
        )
        self.assertEqual(other_map, self.map)

        # Case and space-insensitive match
        other_map = CaseAndSpaceInsensitiveTuplesDict(
            {("Elem 1", "Elem1"): "Value1", ("ELEM 1", "E L E M 2"): 2, (" Elem1 ", "Elem 3"): 3}
        )
        self.assertEqual(other_map, self.map)

    def test_inequality(self):
        # Different value
        other_map = CaseAndSpaceInsensitiveTuplesDict(
            {("Elem1", "Elem1"): "Value1", ("Elem1", "Elem2"): 0, ("Elem1", "Elem3"): 3}
        )
        self.assertNotEqual(other_map, self.map)

        # Partially matching keys with incorrect values
        other_map = CaseAndSpaceInsensitiveTuplesDict(
            {("Elem 1", "Elem1"): "Value1", ("ELEM 1", "E L E M 2"): "wrong", (" Elem1 ", "Elem 3"): 3}
        )
        self.assertNotEqual(other_map, self.map)

        # Completely different key
        other_map = CaseAndSpaceInsensitiveTuplesDict(
            {("wrong", "Elem1"): "Value1", ("Elem1", "Elem2"): 2, ("Elem1", "Elem3"): 3}
        )
        self.assertNotEqual(other_map, self.map)

    def test_get_item(self):
        # Retrieve with case and space insensitivity
        self.assertEqual(self.map[("ELEM1", "ELEM1")], "Value1")
        self.assertEqual(self.map[("elem1", "e l e m 2")], 2)
        self.assertEqual(self.map[("e l e M 1", "elem3")], 3)

    def test_iterate_keys(self):
        # Ensure iteration maintains insertion order
        expected_keys = [("Elem1", "Elem1"), ("Elem1", "Elem2"), ("Elem1", "Elem3")]
        for actual_key, expected_key in zip(self.map, expected_keys):
            self.assertEqual(actual_key, expected_key)

    def test_length(self):
        # Check length
        self.assertEqual(len(self.map), 3)

    def test_set_item(self):
        # Test setting a new item and overriding an existing item
        self.map[("E L E M 1", "E L E M 2")] = 3
        self.assertEqual(self.map[("Elem1", "Elem2")], 3)

        # Add a new entry and check
        self.map[("Elem4", "Elem5")] = 5
        self.assertEqual(len(self.map), 4)
        self.assertEqual(self.map[("Elem4", "Elem5")], 5)

    def test_copy(self):
        # Verify that a copy has the same contents but is a different instance
        copy_map = self.map.copy()
        self.assertIsNot(copy_map, self.map)
        self.assertEqual(copy_map, self.map)

    def test_adjusted_keys(self):
        # Test that adjusted keys return as expected (all keys lowercased and spaceless)
        adjusted_keys = list(self.map.adjusted_keys())
        expected_keys = [("elem1", "elem1"), ("elem1", "elem2"), ("elem1", "elem3")]
        self.assertEqual(adjusted_keys, expected_keys)

    def test_adjusted_items(self):
        # Test adjusted items
        adjusted_items = dict(self.map.adjusted_items())
        expected_items = {("elem1", "elem1"): "Value1", ("elem1", "elem2"): 2, ("elem1", "elem3"): 3}
        self.assertEqual(adjusted_items, expected_items)

    def test_update(self):
        # Test updating with new values
        update_map = {("Elem1", "Elem2"): "Updated", ("Elem1", "NewElem"): 10}
        self.map.update(update_map)

        # Check that updates are applied
        self.assertEqual(self.map[("Elem1", "Elem2")], "Updated")
        self.assertEqual(self.map[("Elem1", "NewElem")], 10)
        self.assertEqual(len(self.map), 4)

    def test_setdefault(self):
        # Existing key with setdefault should return the existing value
        self.assertEqual(self.map.setdefault(("Elem1", "Elem2"), "NewValue"), 2)

        # New key should add the value and return the default
        self.assertEqual(self.map.setdefault(("Elem1", "NewElem"), 10), 10)
        self.assertEqual(self.map[("Elem1", "NewElem")], 10)

    def test_keyerror_on_nonexistent_key(self):
        # Test that a KeyError is raised when accessing a non-existent key
        with self.assertRaises(KeyError):
            _ = self.map[("NonExistent", "Key")]

    def test_contains(self):
        # Test that keys are found with case and space insensitivity
        self.assertIn(("Elem1", "Elem1"), self.map)
        self.assertIn(("elem1", "elem2"), self.map)
        self.assertIn((" e l e m 1 ", " elem 3 "), self.map)
        self.assertNotIn(("NonExistent", "Key"), self.map)

    def test_keys_method(self):
        # Test that keys() returns all keys in original case and insertion order
        expected_keys = [("Elem1", "Elem1"), ("Elem1", "Elem2"), ("Elem1", "Elem3")]
        self.assertEqual(list(self.map.keys()), expected_keys)

    def test_values_method(self):
        # Test that values() returns all values in insertion order
        expected_values = ["Value1", 2, 3]
        self.assertEqual(list(self.map.values()), expected_values)

    def test_items_method(self):
        # Test that items() returns all key-value pairs in original case and insertion order
        expected_items = [(("Elem1", "Elem1"), "Value1"), (("Elem1", "Elem2"), 2), (("Elem1", "Elem3"), 3)]
        self.assertEqual(list(self.map.items()), expected_items)


if __name__ == "__main__":
    unittest.main()

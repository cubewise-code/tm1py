import unittest
from TM1py.Utils.Utils import CaseAndSpaceInsensitiveDict


class TestCaseAndSpaceInsensitiveDict(unittest.TestCase):

    def setUp(self):
        self.map = CaseAndSpaceInsensitiveDict()
        self.map["key1"] = "value1"
        self.map["key2"] = "value2"
        self.map["key3"] = "value3"

    def tearDown(self):
        del self.map

    def test_set_item(self):
        # Test setting new items with case and space variations
        self.map["key4"] = "value4"
        self.assertEqual(self.map["KEY4"], "value4")
        self.assertEqual(self.map["key4"], "value4")
        self.assertEqual(self.map["K e Y 4"], "value4")

    def test_get_item(self):
        # Test getting items with case and space variations
        self.assertEqual(self.map["KEY1"], "value1")
        self.assertEqual(self.map["key2"], "value2")
        self.assertEqual(self.map["K e Y 3"], "value3")

    def test_get_with_default(self):
        # Test getting an item with a default value for non-existing key
        self.assertEqual(self.map.get("nonexistent", "default"), "default")
        self.assertEqual(self.map.get("KEY1", "default"), "value1")

    def test_delete_item(self):
        # Delete items with case and space insensitivity
        del self.map["KEY1"]
        del self.map["key2"]
        del self.map["K e Y 3"]

        # Confirm deletion
        self.assertNotIn("key1", self.map)
        self.assertNotIn("key2", self.map)
        self.assertNotIn("key3", self.map)

    def test_iter(self):
        # Ensure iteration maintains insertion order
        for key1, key2 in zip(self.map, ("key1", "key2", "key3")):
            self.assertEqual(key1, key2)

    def test_len(self):
        # Verify length
        self.assertEqual(len(self.map), 3)
        self.map["key4"] = "value4"
        self.assertEqual(len(self.map), 4)

    def test_copy(self):
        # Verify copy creates a new instance with the same data
        copy_map = self.map.copy()
        self.assertIsNot(copy_map, self.map)
        self.assertEqual(copy_map, self.map)

    def test_equality(self):
        # Exact match
        other_map = CaseAndSpaceInsensitiveDict()
        other_map["key1"] = "value1"
        other_map["key2"] = "value2"
        other_map["key3"] = "value3"
        self.assertEqual(self.map, other_map)

    def test_equality_case_and_space_insensitive(self):
        # Case and space insensitive match
        other_map = CaseAndSpaceInsensitiveDict()
        other_map["key1"] = "value1"
        other_map["KEY2"] = "value2"
        other_map["K e Y 3"] = "value3"
        self.assertEqual(self.map, other_map)

    def test_inequality(self):
        # Mismatched values or additional keys should cause inequality
        other_map = CaseAndSpaceInsensitiveDict({"key 1": "wrong", "key 2": "value2", "key3": "value3"})
        self.assertNotEqual(self.map, other_map)

        other_map = CaseAndSpaceInsensitiveDict({"key1": "value1", "key 2": "wrong", "key3": "value3"})
        self.assertNotEqual(self.map, other_map)

        other_map = CaseAndSpaceInsensitiveDict({"key1": "value1", "key2": "value2", "key4": "value4"})
        self.assertNotEqual(self.map, other_map)

    def test_update(self):
        # Test updating existing and new keys
        update_map = {"KEY1": "new_value1", "new_key": "new_value"}
        self.map.update(update_map)

        self.assertEqual(self.map["key1"], "new_value1")
        self.assertEqual(self.map["new_key"], "new_value")
        self.assertEqual(len(self.map), 4)

    def test_setdefault(self):
        # Existing key should return its value
        self.assertEqual(self.map.setdefault("key1", "default"), "value1")

        # New key should set and return the default value
        self.assertEqual(self.map.setdefault("new_key", "default"), "default")
        self.assertEqual(self.map["new_key"], "default")

    def test_keys(self):
        # Check keys() method for case and insertion order preservation
        expected_keys = ["key1", "key2", "key3"]
        self.assertEqual(list(self.map.keys()), expected_keys)

    def test_values(self):
        # Check values() method for correct values in insertion order
        expected_values = ["value1", "value2", "value3"]
        self.assertEqual(list(self.map.values()), expected_values)

    def test_items(self):
        # Check items() method for correct key-value pairs in insertion order
        expected_items = [("key1", "value1"), ("key2", "value2"), ("key3", "value3")]
        self.assertEqual(list(self.map.items()), expected_items)

    def test_adjusted_keys(self):
        # Test adjusted_keys() to ensure all keys are lowercased and spaceless
        expected_adjusted_keys = ["key1", "key2", "key3"]
        self.assertEqual(list(self.map.adjusted_keys()), expected_adjusted_keys)

    def test_adjusted_items(self):
        # Test adjusted_items() for lowercased, spaceless keys
        expected_adjusted_items = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        adjusted_items = dict(self.map.adjusted_items())
        self.assertEqual(adjusted_items, expected_adjusted_items)

    def test_contains(self):
        # Test in operator with case and space insensitivity
        self.assertIn("key1", self.map)
        self.assertIn("KEY2", self.map)
        self.assertIn("k e y 3", self.map)
        self.assertNotIn("nonexistent_key", self.map)

    def test_keyerror_on_nonexistent_key(self):
        # Confirm that accessing a nonexistent key raises KeyError
        with self.assertRaises(KeyError):
            _ = self.map["nonexistent_key"]


if __name__ == '__main__':
    unittest.main()

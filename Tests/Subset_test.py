import unittest

from TM1py.Objects import AnonymousSubset, Subset


class TestSubset(unittest.TestCase):
    prefix = "TM1py_Tests_Subset_"

    dimension_name = prefix + "dimension"
    hierarchy_name = prefix + "hierarchy"
    subset_name_static = prefix + "static_subset"
    subset_name_dynamic = prefix + "dynamic_subset"
    subset_name_minimal = prefix + "minimal_subset"
    subset_name_complete = prefix + "complete_subset"
    subset_name_alias = prefix + "alias_subset"
    subset_name_anon = prefix + "anon_subset"
    element_name = prefix + "element"

    @classmethod
    def setUpClass(cls):
        """
        Create any class scoped fixtures here.
        """

        cls.subset_dict = {
            "Name": "dict_subset",
            "UniqueName": f"[{cls.dimension_name}]",
            "Hierarchy": {"Name": f"{cls.hierarchy_name}"},
            "Alias": "dict_subset" + "_alias",
            "Elements": [{"Name": "x"}, {"Name": "y"}, {"Name": "z"}],
            "Expression": "",
        }

        cls.subset_json = """
        {
            "Name": "json_subset",
            "UniqueName" : "json_subset",
            "Hierarchy": {
                "Name": "json_subset"
            },
            "Alias": "json_subset_alias",
            "Elements" : [
                {
                    "Name" : "xoy"
                },
                {
                    "Name": "o"
                },
                {
                    "Name": "xxx"
                }            
            ],
            "Expression" : ""
        }
        """

    def setUp(self):
        """
        Instantiate subsets that will be available to all tests.
        """

        self.static_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_static,
            elements=["USD", "EUR", "NZD", "Dum'my"],
        )

        self.dynamic_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_dynamic,
            expression="{ HIERARCHIZE( {TM1SUBSETALL( [" + self.dimension_name + "] )} ) }",
        )

        # subset constructed from only the mandatory arguments
        self.minimal_subset = Subset(dimension_name=self.dimension_name, subset_name=self.subset_name_minimal)

        # a static subset constructed with optional arguments
        self.complete_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_complete,
            hierarchy_name=self.hierarchy_name,
            alias=self.subset_name_alias,
            elements=["a", "b", "c"],
        )

        # an instance of the AnonymoustSubset subclass
        self.anon_subset = AnonymousSubset(
            dimension_name=self.dimension_name, hierarchy_name=self.hierarchy_name, elements=["x", "y", "z"]
        )

    def tearDown(self):
        """
        Remove any artifacts created.
        """
        # nothing required here, all objects will be reset by setUp
        pass

    def test_is_dynamic(self):
        self.assertTrue(self.dynamic_subset.is_dynamic)
        self.assertFalse(self.static_subset.is_dynamic)
        self.assertFalse(self.minimal_subset.is_dynamic)
        self.assertFalse(self.complete_subset.is_dynamic)
        self.assertFalse(self.anon_subset.is_dynamic)

    def test_is_static(self):
        self.assertFalse(self.dynamic_subset.is_static)
        self.assertTrue(self.static_subset.is_static)
        self.assertTrue(self.minimal_subset.is_static)
        self.assertTrue(self.complete_subset.is_static)
        self.assertTrue(self.anon_subset.is_static)

    def test_from_json(self):
        s = Subset.from_json(self.subset_json)
        self.assertEqual(s.name, "json_subset")
        self.assertEqual(s.elements, ["xoy", "o", "xxx"])

    def test_from_dict(self):
        s = Subset.from_dict(self.subset_dict)
        self.assertEqual(s.name, "dict_subset")
        self.assertEqual(s.elements, ["x", "y", "z"])

    def test_add_elements(self):
        self.static_subset.add_elements(["AUD", "CHF"])
        self.assertIn("AUD", self.static_subset.elements)
        self.assertIn("CHF", self.static_subset.elements)

    def test_anonymous_subset(self):
        self.assertEqual(self.anon_subset.name, "")

    def test_property_setters(self):
        self.minimal_subset.elements = ["1", "2", "3"]
        self.assertEqual(self.minimal_subset.elements, ["1", "2", "3"])

    def test_property_getters(self):
        self.assertEqual(self.complete_subset.name, self.subset_name_complete)
        self.assertEqual(self.dynamic_subset.name, self.subset_name_dynamic)
        self.assertEqual(self.static_subset.dimension_name, self.dimension_name)
        self.assertEqual(self.minimal_subset.elements, [])
        self.assertIn("a", self.complete_subset.elements)

    def test_subset_equality(self):
        self.assertNotEqual(self.complete_subset, self.minimal_subset)
        self.assertNotEqual(self.complete_subset, self.anon_subset)
        self.assertNotEqual(self.complete_subset, self.static_subset)
        self.assertNotEqual(self.complete_subset, self.dynamic_subset)
        static_subset_copy = self.static_subset
        self.assertEqual(static_subset_copy, self.static_subset)

    @classmethod
    def tearDownClass(cls):
        """
        Tear down anything as required
        """
        # nothing to do here
        pass


if __name__ == "__main__":
    unittest.main()

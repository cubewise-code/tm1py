import unittest

from TM1py.Objects import Subset, AnonymousSubset

PREFIX = "TM1py_Tests_Subset_"

class TestSubsetMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Create any class scoped fixtures here.
        """
        
        cls.dimension_name = PREFIX + "dimension"
        cls.hierarchy_name = PREFIX + "hierarchy"
        cls.subset_name_static = PREFIX + "static_subset"
        cls.subset_name_dynamic = PREFIX + "dynamic_subset"
        cls.subset_name_minimal = PREFIX + "minimal_subset"
        cls.subset_name_complete = PREFIX + "complete_subset"
        cls.subset_name_alias = PREFIX + "alias_subset"
        cls.subset_name_anon = PREFIX + "anon_subset"

    def setUp(self):
        """
        Instantiate subsets that will be available to all tests.
        """

        self.static_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_static,
            elements=['USD', 'EUR', 'NZD', 'Dum\'my'])
        
        self.dynamic_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_dynamic,
            expression='{ HIERARCHIZE( {TM1SUBSETALL( [' + self.dimension_name + '] )} ) }')

        # subset constructed from only the mandatory arguments
        self.minimal_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_minimal
        )

        # a static subset constructed with optional arguments
        self.complete_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_complete,
            hierarchy_name=self.hierarchy_name,
            alias=self.subset_name_alias,
            elements=["a", "b", "c"]
        )

        # an instance of the AnonymoustSubset subclass
        self.anon_subset = AnonymousSubset(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=["x", "y", "z"]
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
        # test needed - should define a json string in the class
        self.assertTrue(False)

    def test_from_dict(self):
        # test needed - should define a dict in the class
        self.assertTrue(False)

    def test_add_elements(self):
        # test needed - should this fail for dynamic subsets I wonder?
        self.assertTrue(False)

    def test_anonymous_subset(self):
        # test needed - I guess it's a case of testing it has no name property?
        self.assertTrue(False)

    def test_property_setters(self):
        # test needed
        self.assertTrue(False)

    def test_property_getters(self):
        # test needed
        self.assertTrue(False)

    def test_subset_comparisons(self):
        # test needed - check whether they equal one another or not
        self.assertTrue(False)

    @classmethod
    def tearDownClass(cls):
        """
        Tear down anything as required
        """
        pass

if __name__ == '__main__':
    unittest.main()

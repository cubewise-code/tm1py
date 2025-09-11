import configparser
import unittest
import warnings
from pathlib import Path

from TM1py.Objects import Dimension, Hierarchy, Element
from TM1py.Objects import ElementAttribute
from TM1py.Services import TM1Service


class TestDimensionService(unittest.TestCase):
    tm1: TM1Service

    prefix = "TM1py_Tests_Dimension_"
    dimension_name = prefix + "Some_Dimension"
    hierarchy_name = dimension_name
    dimension_name_with_multi_hierarchy = prefix + "Dimension_With_Multiple_Hierarchies"

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath("config.ini"))
        cls.tm1 = TM1Service(**cls.config["tm1srv01"])

    def setUp(self):
        self.create_dimensions()

    def tearDown(self):
        self.delete_dimensions()

    @classmethod
    def create_dimensions(cls):
        root_element = Element(name="Root", element_type="Consolidated")
        elements = [root_element]
        edges = {}
        for i in range(1, 1001):
            element_name = "Element {}".format(i)
            elements.append(Element(name=element_name, element_type="Numeric"))
            edges[("Root", element_name)] = i
        element_attributes = [
            ElementAttribute(name="Name Long", attribute_type="Alias"),
            ElementAttribute(name="Name Short", attribute_type="Alias"),
        ]
        h = Hierarchy(
            name=cls.dimension_name,
            dimension_name=cls.dimension_name,
            elements=elements,
            edges=edges,
            element_attributes=element_attributes,
        )
        d = Dimension(name=cls.dimension_name, hierarchies=[h])
        cls.tm1.dimensions.update_or_create(d)

        cls.create_or_update_dimension_with_multiple_hierarchies()

    @classmethod
    def create_or_update_dimension_with_multiple_hierarchies(cls):
        dimension = Dimension(cls.dimension_name_with_multi_hierarchy)
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy1",
                dimension_name=dimension.name,
                elements=[Element("Elem1", "Numeric"), Element("Elem2", "Numeric"), Element("Elem3", "Numeric")],
            )
        )
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy2",
                dimension_name=dimension.name,
                elements=[Element("Elem1", "Numeric"), Element("Elem2", "Numeric"), Element("Elem3", "Numeric")],
            )
        )
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy3",
                dimension_name=dimension.name,
                elements=[Element("Elem1", "Numeric"), Element("Elem2", "Numeric"), Element("Elem3", "Numeric")],
            )
        )
        cls.tm1.dimensions.update_or_create(dimension)

    @classmethod
    def delete_dimensions(cls):
        cls.tm1.dimensions.delete(cls.dimension_name)
        if cls.tm1.dimensions.exists(cls.dimension_name_with_multi_hierarchy):
            cls.tm1.dimensions.delete(cls.dimension_name_with_multi_hierarchy)

    def test_get_dimension(self):
        d = self.tm1.dimensions.get(dimension_name=self.dimension_name)
        self.assertIsInstance(d, Dimension)
        self.assertEqual(d.name, self.dimension_name)
        h = d.hierarchies[0]
        self.assertIsInstance(h, Hierarchy)
        self.assertEqual(h.name, self.dimension_name)
        self.assertEqual(len(h.elements), 1001)
        self.assertEqual(len(h.edges), 1000)

    def test_dimension__get__(self):
        d = self.tm1.dimensions.get(dimension_name=self.dimension_name)
        h = d[self.dimension_name]
        self.assertIsInstance(h, Hierarchy)
        self.assertEqual(h.name, self.dimension_name)
        self.assertEqual(len(h.elements), 1001)
        self.assertEqual(len(h.edges), 1000)

    def test_dimension__contains__(self):
        d = self.tm1.dimensions.get(dimension_name=self.dimension_name)
        self.assertIn(self.dimension_name, d)

    def test_dimension__iter__(self):
        d = self.tm1.dimensions.get(dimension_name=self.dimension_name)
        first_hierarchy = next(h for h in d)
        self.assertIsInstance(first_hierarchy, Hierarchy)
        self.assertEqual(first_hierarchy.name, self.dimension_name)
        self.assertEqual(len(first_hierarchy.elements), 1001)
        self.assertEqual(len(first_hierarchy.edges), 1000)

    def test_dimension__len__(self):
        d = self.tm1.dimensions.get(dimension_name=self.dimension_name)
        self.assertEqual(len(d), 1)

    def test_update_dimension(self):
        # get dimension from tm1
        d = self.tm1.dimensions.get(dimension_name=self.dimension_name)
        # create element objects
        elements = [
            Element(name="e1", element_type="Consolidated"),
            Element(name="e2", element_type="Numeric"),
            Element(name="e3", element_type="Numeric"),
            Element(name="e4", element_type="Numeric"),
        ]
        # create edge objects
        edges = {("e1", "e2"): 1, ("e1", "e3"): 1, ("e1", "e4"): 1}
        # create the element_attributes objects
        element_attributes = [
            ElementAttribute(name="Name Long", attribute_type="Alias"),
            ElementAttribute(name="Name Short", attribute_type="Alias"),
            ElementAttribute(name="Currency", attribute_type="String"),
        ]
        # create hierarchy object
        hierarchy = Hierarchy(
            name=self.dimension_name,
            dimension_name=self.dimension_name,
            elements=elements,
            element_attributes=element_attributes,
            edges=edges,
        )

        # replace existing hierarchy with new hierarchy
        d.remove_hierarchy(self.dimension_name)
        d.add_hierarchy(hierarchy)

        # update dimension in TM1
        self.tm1.dimensions.update(d)

        # Test
        dimension = self.tm1.dimensions.get(self.dimension_name)
        self.assertEqual(len(dimension.hierarchies[0].elements), len(elements))

    def test_update_dimension_without_leaves(self):
        dimension = self.tm1.dimensions.get(self.dimension_name_with_multi_hierarchy)
        self.assertEqual(dimension.hierarchy_names, ["Hierarchy1", "Hierarchy2", "Hierarchy3", "Leaves"])
        dimension.remove_hierarchy("Hierarchy2")
        dimension.remove_hierarchy("Hierarchy3")
        dimension._hierarchies = [hierarchy for hierarchy in dimension._hierarchies if not hierarchy.name == "Leaves"]

        # Test that TM1py does not attempt to delete the leaves hierarchy
        self.tm1.dimensions.update(dimension)
        dimension = self.tm1.dimensions.get(self.dimension_name_with_multi_hierarchy)
        self.assertEqual(dimension.hierarchy_names, ["Hierarchy1", "Leaves"])

    def test_update_dimension_remove_hierarchy(self):
        dimension = self.tm1.dimensions.get(self.dimension_name_with_multi_hierarchy)
        self.assertEqual(dimension.hierarchy_names, ["Hierarchy1", "Hierarchy2", "Hierarchy3", "Leaves"])
        dimension.remove_hierarchy("Hierarchy2")
        dimension.remove_hierarchy("Hierarchy3")
        self.tm1.dimensions.update(dimension)
        dimension = self.tm1.dimensions.get(self.dimension_name_with_multi_hierarchy)
        self.assertEqual(dimension.hierarchy_names, ["Hierarchy1", "Leaves"])

    def test_get_all_names(self):
        self.assertIn(self.dimension_name, self.tm1.dimensions.get_all_names())
        self.assertNotEqual(
            self.tm1.dimensions.get_all_names(), self.tm1.dimensions.get_all_names(skip_control_dims=True)
        )

    def test_get_number_of_dimensions(self):
        number_of_dimensions = self.tm1.dimensions.get_number_of_dimensions()
        self.assertIsInstance(number_of_dimensions, int)
        self.assertNotEqual(
            self.tm1.dimensions.get_number_of_dimensions(),
            self.tm1.dimensions.get_number_of_dimensions(skip_control_dims=True),
        )

    def test_execute_mdx(self):
        mdx = "{TM1SubsetAll(" + self.dimension_name + ")}"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            elements = self.tm1.dimensions.execute_mdx(self.dimension_name, mdx)
        self.assertEqual(len(elements), 1001)

        mdx = "{ Tm1FilterByLevel ( {TM1SubsetAll(" + self.dimension_name + ")}, 0) }"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            elements = self.tm1.dimensions.execute_mdx(self.dimension_name, mdx)
        self.assertEqual(len(elements), 1000)

        for element in elements:
            self.assertTrue(element.startswith("Element"))

    def test_hierarchy_names(self):
        dimension = self.tm1.dimensions.get(dimension_name=self.dimension_name_with_multi_hierarchy)
        self.assertEqual(set(dimension.hierarchy_names), {"Leaves", "Hierarchy1", "Hierarchy2", "Hierarchy3"})

        dimension.remove_hierarchy("Hierarchy1")
        self.assertEqual(set(dimension.hierarchy_names), {"Leaves", "Hierarchy2", "Hierarchy3"})

    def test_remove_leaves_hierarchy(self):
        dimension = self.tm1.dimensions.get(dimension_name=self.dimension_name_with_multi_hierarchy)
        self.assertRaises(ValueError, dimension.remove_hierarchy, "LEAVES")

    def test_remove_hierarchy(self):
        dimension = self.tm1.dimensions.get(dimension_name=self.dimension_name_with_multi_hierarchy)
        self.assertEqual(len(dimension.hierarchies), 4)
        self.assertIn("Hierarchy1", dimension)
        self.assertIn("Hierarchy2", dimension)
        self.assertIn("Hierarchy3", dimension)
        self.assertIn("Leaves", dimension)

        dimension.remove_hierarchy("Hierarchy1")
        self.tm1.dimensions.update(dimension)

        dimension = self.tm1.dimensions.get(dimension_name=self.dimension_name_with_multi_hierarchy)
        self.assertEqual(len(dimension.hierarchies), 3)
        self.assertNotIn("Hierarchy1", dimension)
        self.assertIn("Hierarchy2", dimension)
        self.assertIn("Hierarchy3", dimension)
        self.assertIn("Leaves", dimension)

        dimension.remove_hierarchy("H i e r a r c h y 3".upper())
        self.tm1.dimensions.update(dimension)

        dimension = self.tm1.dimensions.get(dimension_name=self.dimension_name_with_multi_hierarchy)
        self.assertEqual(len(dimension.hierarchies), 2)
        self.assertNotIn("Hierarchy1", dimension)
        self.assertIn("Hierarchy2", dimension)
        self.assertNotIn("Hierarchy3", dimension)
        self.assertIn("Leaves", dimension)

    def test_rename_dimension(self):
        original_dimension_name = self.prefix + "Original_Dimension"
        renamed_dimension_name = self.prefix + "Renamed_Dimension"

        # if dimensions exist in TM1.. delete them
        for dim_name in (original_dimension_name, renamed_dimension_name):
            if self.tm1.dimensions.exists(dim_name):
                self.tm1.dimensions.delete(dimension_name=dim_name)

        # create dimension
        original_dimension = Dimension(original_dimension_name)
        hierarchy = Hierarchy(name=original_dimension_name, dimension_name=original_dimension_name)
        hierarchy.add_element(element_name="Total", element_type="Consolidated")
        hierarchy.add_element(element_name="Elem1", element_type="Numeric")
        hierarchy.add_element(element_name="Elem2", element_type="Numeric")
        hierarchy.add_element(element_name="Elem3", element_type="Numeric")
        hierarchy.add_edge(parent="Total", component="Elem1", weight=1)
        hierarchy.add_edge(parent="Total", component="Elem2", weight=1)
        hierarchy.add_edge(parent="Total", component="Elem3", weight=1)
        original_dimension.add_hierarchy(hierarchy)
        self.tm1.dimensions.create(original_dimension)

        # rename
        renamed_dimension = self.tm1.dimensions.get(original_dimension.name)
        renamed_dimension.name = renamed_dimension_name
        self.tm1.dimensions.create(renamed_dimension)

        # challenge equality of dimensions
        summary1 = self.tm1.dimensions.hierarchies.get_hierarchy_summary(
            dimension_name=original_dimension_name, hierarchy_name=original_dimension_name
        )
        summary2 = self.tm1.dimensions.hierarchies.get_hierarchy_summary(
            dimension_name=renamed_dimension_name, hierarchy_name=renamed_dimension_name
        )
        self.assertEqual(summary1, summary2)

        # delete
        for dim_name in (original_dimension_name, renamed_dimension_name):
            self.tm1.dimensions.delete(dimension_name=dim_name)

    def test_uses_hierarchies_true(self):
        self.assertTrue(
            self.tm1.dimensions.uses_alternate_hierarchies(dimension_name=self.dimension_name_with_multi_hierarchy)
        )

    def test_uses_hierarchies_false(self):
        self.assertFalse(self.tm1.dimensions.uses_alternate_hierarchies(dimension_name=self.dimension_name))

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == "__main__":
    unittest.main()

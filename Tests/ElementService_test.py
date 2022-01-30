import configparser
import unittest
from pathlib import Path

from TM1py.Exceptions import TM1pyRestException
from TM1py.Objects import Dimension, Hierarchy, Element, ElementAttribute
from TM1py.Services import TM1Service


class TestElementService(unittest.TestCase):
    tm1: TM1Service

    prefix = 'TM1py_unittest_element_'
    dimension_name = f"{prefix}_dimension"
    dimension_with_hierarchies_name = f"{prefix}_dimension_with_hierarchies"
    hierarchy_name = dimension_name
    attribute_cube_name = '}ElementAttributes_' + dimension_name

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM1 objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])

    @classmethod
    def setUp(cls):
        # create dimension with a default hierarchy
        d = Dimension(cls.dimension_name)
        h = Hierarchy(cls.dimension_name, cls.hierarchy_name)

        # add elements
        cls.years = ("No Year", "1989", "1990", "1991", "1992")
        cls.extra_year = "4321"

        h.add_element('Total Years', 'Consolidated')
        h.add_element('All Consolidations', 'Consolidated')
        h.add_edge("All Consolidations", "Total Years", 1)
        for year in cls.years:
            h.add_element(year, 'Numeric')
            h.add_edge('Total Years', year, 1)

        # add attributes
        cls.attributes = ('Previous Year', 'Next Year')
        cls.alias_attributes = ("Financial Year",)

        for attribute in cls.attributes:
            h.add_element_attribute(attribute, "String")
        for attribute in cls.alias_attributes:
            h.add_element_attribute(attribute, "Alias")
        d.add_hierarchy(h)
        cls.tm1.dimensions.create(d)

        cls.added_attribute_name = "NewAttribute"

        # write attribute values
        cls.tm1.cubes.cells.write_value('1988', cls.attribute_cube_name, ('1989', 'Previous Year'))
        cls.tm1.cubes.cells.write_value('1989', cls.attribute_cube_name, ('1990', 'Previous Year'))
        cls.tm1.cubes.cells.write_value('1990', cls.attribute_cube_name, ('1991', 'Previous Year'))
        cls.tm1.cubes.cells.write_value('1991', cls.attribute_cube_name, ('1992', 'Previous Year'))

        cls.tm1.cubes.cells.write_value('1988/89', cls.attribute_cube_name, ('1989', 'Financial Year'))
        cls.tm1.cubes.cells.write_value('1989/90', cls.attribute_cube_name, ('1990', 'Financial Year'))
        cls.tm1.cubes.cells.write_value('1990/91', cls.attribute_cube_name, ('1991', 'Financial Year'))
        cls.tm1.cubes.cells.write_value('1991/92', cls.attribute_cube_name, ('1992', 'Financial Year'))

        cls.create_or_update_dimension_with_hierarchies()

    @classmethod
    def tearDown(cls):
        cls.tm1.dimensions.delete(cls.dimension_name)
        cls.tm1.dimensions.delete(cls.dimension_with_hierarchies_name)

    @classmethod
    def create_or_update_dimension_with_hierarchies(cls):
        dimension = Dimension(cls.dimension_with_hierarchies_name)
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy1",
                dimension_name=dimension.name,
                elements=[Element("Elem1", "Numeric"), Element("Elem2", "Numeric"), Element("Elem3", "Numeric")]))
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy2",
                dimension_name=dimension.name,
                elements=[Element("Elem4", "Numeric"), Element("Elem6", "Numeric"), Element("Cons1", "Consolidated")]))
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy3",
                dimension_name=dimension.name,
                elements=[Element("Elem5", "Numeric"), Element("Cons2", "Consolidated"),
                          Element("Cons3", "Consolidated")]))
        cls.tm1.dimensions.update_or_create(dimension)

    def test_create_and_delete_element(self):
        element = Element(self.extra_year, "String")
        self.tm1.dimensions.hierarchies.elements.create(
            self.dimension_name,
            self.hierarchy_name,
            element)

        element_returned = self.tm1.dimensions.hierarchies.elements.get(
            self.dimension_name,
            self.hierarchy_name,
            element.name)
        self.assertEqual(element, element_returned)

        self.tm1.dimensions.hierarchies.elements.delete(
            self.dimension_name,
            self.hierarchy_name,
            element.name)

    def test_get_element(self):
        for element_name in self.years:
            element = self.tm1.dimensions.hierarchies.elements.get(
                self.dimension_name,
                self.hierarchy_name,
                element_name)
            self.assertEqual(element.name, element_name)

    def test_update_element(self):
        element = Element(self.extra_year, Element.Types("S T R I N G"))
        self.tm1.dimensions.hierarchies.elements.create(
            self.dimension_name,
            self.hierarchy_name,
            element)

        element_name = self.extra_year
        element = self.tm1.dimensions.hierarchies.elements.get(self.dimension_name, self.hierarchy_name, element_name)
        element.element_type = "Numeric"
        self.tm1.dimensions.hierarchies.elements.update(self.dimension_name, self.hierarchy_name, element)

        element = self.tm1.dimensions.hierarchies.elements.get(self.dimension_name, self.hierarchy_name, element_name)
        self.assertTrue(element.element_type == Element.Types.NUMERIC)

        self.tm1.dimensions.hierarchies.elements.delete(
            self.dimension_name,
            self.hierarchy_name,
            element.name)

    def test_get_element_attributes(self):
        element_attributes = self.tm1.dimensions.hierarchies.elements.get_element_attributes(
            self.dimension_name,
            self.hierarchy_name)
        self.assertIn('Previous Year', element_attributes)
        self.assertIn('Next Year', element_attributes)

    def test_get_elements_filtered_by_attribute(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_attribute(
            self.dimension_name,
            self.hierarchy_name,
            'Previous Year',
            '1988')
        self.assertIn('1989', elements)

    def test_get_element_by_attribute_without_elements(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_attribute_of_elements(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            attribute='Previous Year')
        self.assertEqual('1989', elements['1990'])
        self.assertEqual('1990', elements['1991'])
        self.assertNotIn(self.extra_year, elements)
        self.assertIsInstance(elements, dict)

    def test_get_element_by_attribute_with_elements(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_attribute_of_elements(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=["1990", "1991"],
            attribute="Previous Year",
            element_unique_names=True)
        self.assertNotIn("[" + self.dimension_name + "]." + "[" + self.hierarchy_name + "]." + "[1989]", elements)
        self.assertEqual("1989",
                         elements["[" + self.dimension_name + "]." + "[" + self.hierarchy_name + "]." + "[1990]"])
        self.assertIn("[" + self.dimension_name + "]." + "[" + self.hierarchy_name + "]." + "[1991]", elements)
        self.assertIsInstance(elements, dict)

    def test_create_filter_and_delete_element_attribute(self):
        attribute = ElementAttribute('Leap Year', 'Numeric')
        self.tm1.dimensions.hierarchies.elements.create_element_attribute(
            self.dimension_name,
            self.hierarchy_name, attribute)
        # write one element attribute value
        self.tm1.cubes.cells.write_value(
            1,
            '}ElementAttributes_' + self.dimension_name,
            ('1992', 'Leap Year'))
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_attribute(
            self.dimension_name,
            self.hierarchy_name,
            'Leap Year', 1)
        self.assertIn('1992', elements)
        self.assertEqual(len(elements), 1)

        self.tm1.dimensions.hierarchies.elements.delete_element_attribute(
            self.dimension_name,
            self.hierarchy_name,
            "Leap Year")

    def test_get_elements(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_elements(
            self.dimension_name,
            self.hierarchy_name)
        element_names = [element.name for element in elements]
        for year in self.years:
            self.assertIn(year, element_names)
        self.assertNotIn(self.extra_year, element_names)

    def test_get_element_names(self):
        element_names = self.tm1.dimensions.hierarchies.elements.get_element_names(
            self.dimension_name,
            self.hierarchy_name)
        for year in self.years:
            self.assertIn(year, element_names)

    def test_get_leaf_element_names(self):
        leaf_element_names = self.tm1.dimensions.hierarchies.elements.get_leaf_element_names(
            self.dimension_name,
            self.hierarchy_name)
        for leaf in leaf_element_names:
            self.assertIn(leaf, self.years)
        self.assertNotIn(self.extra_year, leaf_element_names)
        self.assertNotIn("Total Years", leaf_element_names)

    def test_get_leaf_elements(self):
        leaf_elements = self.tm1.dimensions.hierarchies.elements.get_leaf_elements(
            self.dimension_name,
            self.hierarchy_name)
        for leaf in leaf_elements:
            self.assertIn(leaf.name, self.years)
            self.assertNotEqual(leaf.element_type, "Consolidated")
        leaf_element_names = [element.name for element in leaf_elements]
        self.assertNotIn(self.extra_year, leaf_element_names)
        self.assertNotIn("Total Year", leaf_element_names)

    def test_element_exists(self):
        for year in self.years:
            self.assertTrue(self.tm1.dimensions.hierarchies.elements.exists(
                self.dimension_name,
                self.hierarchy_name,
                year))

    def test_get_leaves_under_consolidation(self):
        leaves = self.tm1.dimensions.hierarchies.elements.get_leaves_under_consolidation(
            self.dimension_name,
            self.hierarchy_name,
            "All Consolidations")
        self.assertNotIn("Total Years", leaves)
        for year in self.years:
            self.assertIn(year, leaves)

    def test_get_members_under_consolidation(self):
        leaves = self.tm1.dimensions.hierarchies.elements.get_members_under_consolidation(
            self.dimension_name,
            self.hierarchy_name,
            "All Consolidations",
            leaves_only=True)
        self.assertNotIn("Total Years", leaves)
        for year in self.years:
            self.assertIn(year, leaves)

        members = self.tm1.dimensions.hierarchies.elements.get_members_under_consolidation(
            self.dimension_name,
            self.hierarchy_name,
            "All Consolidations",
            leaves_only=False)
        self.assertIn("Total Years", members)
        for year in self.years:
            self.assertIn(year, members)

    def test_get_element_identifiers_with_iterable(self):
        expected_identifiers = {'1988/89', '1989/90', '1990/91', '1991/92', *self.years}
        elements = self.years
        identifiers = self.tm1.dimensions.hierarchies.elements.get_element_identifiers(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=elements)
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_element_identifiers_with_string(self):
        expected_identifiers = {'1988/89', '1989/90', '1990/91', '1991/92', *self.years}
        elements = "{" + ",".join(["[" + self.dimension_name + "].[" + year + "]" for year in self.years]) + "}"
        identifiers = self.tm1.dimensions.hierarchies.elements.get_element_identifiers(
            dimension_name=self.dimension_name,
            hierarchy_name=self.hierarchy_name,
            elements=elements)
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_all_element_identifiers(self):
        expected_identifiers = {'1988/89', '1989/90', '1990/91', '1991/92', 'Total Years', 'All Consolidations',
                                *self.years}
        identifiers = self.tm1.dimensions.hierarchies.elements.get_all_element_identifiers(
            self.dimension_name,
            self.hierarchy_name)
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_all_leaf_element_identifiers(self):
        expected_identifiers = {'1988/89', '1989/90', '1990/91', '1991/92', *self.years}
        identifiers = self.tm1.dimensions.hierarchies.elements.get_all_leaf_element_identifiers(
            self.dimension_name,
            self.hierarchy_name)
        self.assertEqual(expected_identifiers, set(identifiers))

    def test_get_elements_by_level(self):
        expected_elements = ['No Year', '1989', '1990', '1991', '1992']
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_by_level(
            self.dimension_name, self.hierarchy_name, 0)

        self.assertEqual(elements, expected_elements)

        expected_elements = ['Total Years']
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_by_level(
            self.dimension_name, self.hierarchy_name, 1)
        self.assertEqual(elements, expected_elements)

    def test_get_elements_by_wildcard(self):
        expected_elements = ['Total Years', 'No Year']
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_wildcard(
            self.dimension_name, self.hierarchy_name, 'year')
        self.assertEqual(elements, expected_elements)

        expected_elements = ['Total Years']
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_wildcard(
            self.dimension_name, self.hierarchy_name, 'talyear', 1)
        self.assertEqual(elements, expected_elements)

        expected_elements = ['1989', '1990', '1991', '1992']
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_wildcard(
            self.dimension_name, self.hierarchy_name, '19', 0)
        self.assertEqual(elements, expected_elements)

        expected_elements = ['1990', '1991', '1992']
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_wildcard(
            self.dimension_name, self.hierarchy_name, '99', 0)
        self.assertEqual(elements, expected_elements)

    def test_get_number_of_elements(self):
        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_elements(
            self.dimension_name, self.hierarchy_name)
        self.assertEqual(number_of_elements, 7)

    def test_get_number_of_leaf_elements(self):
        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_leaf_elements(
            self.dimension_name, self.hierarchy_name)

        self.assertEqual(number_of_elements, 5)

    def test_get_number_of_consolidated_elements(self):
        number_of_elements = self.tm1.dimensions.hierarchies.elements.get_number_of_consolidated_elements(
            self.dimension_name, self.hierarchy_name)

        self.assertEqual(number_of_elements, 2)

    def test_create_element_attribute(self):
        element_attribute = ElementAttribute("NewAttribute", "String")
        self.tm1.dimensions.hierarchies.elements.create_element_attribute(
            self.dimension_name,
            self.dimension_name,
            element_attribute)

        element_attributes = self.tm1.dimensions.hierarchies.elements.get_element_attributes(
            self.dimension_name,
            self.dimension_name)

        self.assertIn(element_attribute, element_attributes)

    def test_delete_element_attribute(self):
        element_attribute = ElementAttribute("NewAttribute", "String")
        self.tm1.dimensions.hierarchies.elements.create_element_attribute(
            self.dimension_name,
            self.dimension_name,
            element_attribute)

        self.tm1.dimensions.hierarchies.elements.delete_element_attribute(
            self.dimension_name,
            self.dimension_name,
            element_attribute.name)

        element_attributes = self.tm1.dimensions.hierarchies.elements.get_element_attributes(
            self.dimension_name,
            self.dimension_name)

        self.assertNotIn(element_attribute, element_attributes)

    def test_add_edge_single(self):
        consolidation = Element(name="Consolidation", element_type="Consolidated")
        element = Element(name="Element", element_type="Numeric")
        self.tm1.elements.add_elements(self.dimension_name, self.dimension_name, [consolidation, element])

        edge = {(consolidation.name, element.name): 2}
        self.tm1.elements.add_edges(self.dimension_name, self.hierarchy_name, edge)

        all_edges = self.tm1.elements.get_edges(self.dimension_name, self.dimension_name)
        self.assertIn((consolidation.name, element.name), all_edges)
        self.assertEqual(2, all_edges[consolidation.name, element.name])

    def test_add_edge_multi(self):
        consolidation = Element(name="Consolidation", element_type="Consolidated")
        element1 = Element(name="Element1", element_type="Numeric")
        element2 = Element(name="Element2", element_type="Numeric")
        self.tm1.elements.add_elements(self.dimension_name, self.dimension_name, [consolidation, element1, element2])

        edges = {(consolidation.name, element1.name): 2, (consolidation.name, element2.name): 3}
        self.tm1.elements.add_edges(self.dimension_name, self.hierarchy_name, edges)

        all_edges = self.tm1.elements.get_edges(self.dimension_name, self.dimension_name)
        self.assertIn((consolidation.name, element1.name), all_edges)
        self.assertIn((consolidation.name, element2.name), all_edges)
        self.assertEqual(2, all_edges[consolidation.name, element1.name])
        self.assertEqual(3, all_edges[consolidation.name, element2.name])

    def test_add_edge_fail(self):
        with self.assertRaises(TM1pyRestException) as _:
            edges = {("NotExisting1", "NotExisting2"): 1}
            self.tm1.elements.add_edges(self.dimension_name, self.dimension_name, edges)

    def test_add_elements_single(self):
        element = Element(name="Element0", element_type="Numeric")
        self.tm1.elements.add_elements(self.dimension_name, self.dimension_name, [element])

        self.assertEqual(element, self.tm1.elements.get(self.dimension_name, self.dimension_name, element.name))

    def test_add_elements_multi(self):
        element1 = Element(name="Element1", element_type="Numeric")
        element2 = Element(name="Element2", element_type="Numeric")
        self.tm1.elements.add_elements(self.dimension_name, self.dimension_name, [element1, element2])

        self.assertEqual(element1, self.tm1.elements.get(self.dimension_name, self.dimension_name, element1.name))
        self.assertEqual(element2, self.tm1.elements.get(self.dimension_name, self.dimension_name, element2.name))

    def test_add_elements_fail(self):
        with self.assertRaises(TM1pyRestException) as _:
            element = Element(self.years[0], "Numeric")
            self.tm1.elements.add_elements(self.dimension_name, self.dimension_name, [element])

    def test_add_element_attributes_single(self):
        element_attribute = ElementAttribute(name="Attribute1", attribute_type="String")
        self.tm1.elements.add_element_attributes(self.dimension_name, self.dimension_name, [element_attribute])

        self.assertIn(
            element_attribute,
            self.tm1.elements.get_element_attributes(self.dimension_name, self.dimension_name))

    def test_add_element_attributes_multi(self):
        element_attribute1 = ElementAttribute(name="Attribute1", attribute_type="String")
        element_attribute2 = ElementAttribute(name="Attribute2", attribute_type="String")
        self.tm1.elements.add_element_attributes(
            self.dimension_name,
            self.dimension_name,
            [element_attribute1, element_attribute2])

        self.assertIn(
            element_attribute1,
            self.tm1.elements.get_element_attributes(self.dimension_name, self.dimension_name))
        self.assertIn(
            element_attribute2,
            self.tm1.elements.get_element_attributes(self.dimension_name, self.dimension_name))

    def test_add_element_attributes_fail(self):
        with self.assertRaises(TM1pyRestException) as _:
            element_attribute = ElementAttribute(name=self.attributes[0], attribute_type="String")

            self.tm1.elements.add_element_attributes(
                self.dimension_name,
                self.dimension_name,
                [element_attribute])

    def test_execute_set_mdx(self):
        mdx = f"{{[{self.dimension_name}].[1990]}}"
        members = self.tm1.elements.execute_set_mdx(
            mdx=mdx,
            member_properties=["Name"],
            element_properties=None,
            parent_properties=None)

        self.assertEqual(members, [[{'Name': '1990'}]])

    def test_execute_set_mdx_attribute_with_space(self):
        mdx = f"{{[{self.dimension_name}].[1990]}}"
        members = self.tm1.elements.execute_set_mdx(
            mdx=mdx,
            member_properties=["Name", "Attributes/Previous Year"],
            element_properties=None,
            parent_properties=None)

        self.assertEqual(members, [[{'Name': '1990', 'Attributes': {'Previous Year': '1989'}}]])

    def test_get_element_types(self):
        element_types = self.tm1.elements.get_element_types(self.dimension_name, self.hierarchy_name)
        expected = {
            "No Year": "Numeric",
            "1989": "Numeric",
            "1990": "Numeric",
            "1991": "Numeric",
            "1992": "Numeric",
            "Total Years": "Consolidated",
            "All Consolidations": "Consolidated"
        }
        self.assertEqual(expected, element_types)

    def test_get_element_types_from_all_hierarchies_with_single_hierarchy(self):
        expected = {
            "No Year": "Numeric",
            "1989": "Numeric",
            "1990": "Numeric",
            "1991": "Numeric",
            "1992": "Numeric",
            "Total Years": "Consolidated",
            "All Consolidations": "Consolidated"
        }
        element_types = self.tm1.elements.get_element_types_from_all_hierarchies(self.dimension_name)
        self.assertEqual(expected, element_types)

    def test_get_element_types_from_all_hierarchies(self):
        expected = {
            "Elem1": "Numeric",
            "Elem2": "Numeric",
            "Elem3": "Numeric",
            "Elem4": "Numeric",
            "Elem5": "Numeric",
            "Elem6": "Numeric",
            "Cons1": "Consolidated",
            "Cons2": "Consolidated",
            "Cons3": "Consolidated"
        }
        element_types = self.tm1.elements.get_element_types_from_all_hierarchies(
            self.dimension_with_hierarchies_name)

        self.assertEqual(expected, element_types)

    def test_get_element_types_from_all_hierarchies_skip_consolidations(self):

        expected = {
            "Elem1": "Numeric",
            "Elem2": "Numeric",
            "Elem3": "Numeric",
            "Elem4": "Numeric",
            "Elem5": "Numeric",
            "Elem6": "Numeric",
        }
        element_types = self.tm1.elements.get_element_types_from_all_hierarchies(
            dimension_name=self.dimension_with_hierarchies_name,
            skip_consolidations=True)

        self.assertEqual(expected, element_types)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()

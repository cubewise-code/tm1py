import configparser
from pathlib import Path
import unittest
import uuid

from TM1py.Objects import Dimension, Hierarchy, Element, ElementAttribute
from TM1py.Services import TM1Service

class TestElementMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM! objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])

        cls.prefix = 'TM1py_unittest_element_'
        cls.dimension_name = f"{cls.prefix}{uuid.uuid4()}"
        cls.hierarchy_name = cls.dimension_name
        cls.attribute_cube_name = '}ElementAttributes_' + cls.dimension_name

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

    @classmethod
    def setUp(cls):

        # write attribute values
        cls.tm1.cubes.cells.write_value('1988', cls.attribute_cube_name, ('1989', 'Previous Year'))
        cls.tm1.cubes.cells.write_value('1989', cls.attribute_cube_name, ('1990', 'Previous Year'))
        cls.tm1.cubes.cells.write_value('1990', cls.attribute_cube_name, ('1991', 'Previous Year'))
        cls.tm1.cubes.cells.write_value('1991', cls.attribute_cube_name, ('1992', 'Previous Year'))

        cls.tm1.cubes.cells.write_value('1988/89', cls.attribute_cube_name, ('1989', 'Financial Year'))
        cls.tm1.cubes.cells.write_value('1989/90', cls.attribute_cube_name, ('1990', 'Financial Year'))
        cls.tm1.cubes.cells.write_value('1990/91', cls.attribute_cube_name, ('1991', 'Financial Year'))
        cls.tm1.cubes.cells.write_value('1991/92', cls.attribute_cube_name, ('1992', 'Financial Year'))

    @classmethod
    def tearDown(cls):
        
        cls.tm1.processes.execute_ti_code("CubeClearData('" + cls.attribute_cube_name + "');")
        
        # remove added attribute if exists
        if cls.added_attribute_name in cls.tm1.dimensions.hierarchies.elements.get_element_attributes(
            cls.dimension_name,
            cls.dimension_name):
        
            cls.tm1.dimensions.hierarchies.elements.delete_element_attribute(
                cls.dimension_name,
                cls.dimension_name,
                cls.added_attribute_name)

    def add_unbalanced_hierarchy(self, hierarchy_name):
        dimension = self.tm1.dimensions.get(self.dimension_name)
        
        # other hierarchy
        hierarchy = Hierarchy(name=hierarchy_name, dimension_name=self.dimension_name)

        hierarchy.add_element("Total Years Unbalanced", "Consolidated")
        hierarchy.add_element('1989', 'Numeric')
        hierarchy.add_element('1990', 'Numeric')
        hierarchy.add_element('1991', 'Numeric')
        hierarchy.add_edge("Total Years Unbalanced", "1989", 1)
        hierarchy.add_edge("Total Years Unbalanced", "1990", 1)
        dimension.add_hierarchy(hierarchy)

        self.tm1.dimensions.update(dimension)

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
        self.assertEqual("1989", elements["[" + self.dimension_name + "]." + "[" + self.hierarchy_name + "]." + "[1990]"])
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

    @classmethod
    def tearDownClass(cls):
        cls.tm1.dimensions.delete(cls.dimension_name)
        cls.tm1.logout()



if __name__ == '__main__':
    unittest.main()

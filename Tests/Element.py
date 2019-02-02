import configparser
import os
import unittest
import uuid

from TM1py.Objects import Dimension, Hierarchy, Element, ElementAttribute
from TM1py.Services import TM1Service

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))

DIMENSION_PREFIX = 'TM1py_unittest_element_{}'
DIMENSION_NAME = DIMENSION_PREFIX.format(uuid.uuid4())
HIERARCHY_NAME = DIMENSION_NAME


class TestElementMethods(unittest.TestCase):
    tm1 = None

    @classmethod
    def setup_class(cls):

        # Connection to TM1
        cls.tm1 = TM1Service(**config['tm1srv01'])

    @classmethod
    def setUp(cls):
        # Elements
        cls.years = ("No Year", "1989", "1990", "1991", "1992")
        cls.extra_year = "4321"
        # Element Attributes
        cls.attributes = ('Previous Year', 'Next Year')

        # create dimension with a default hierarchy
        d = Dimension(DIMENSION_NAME)
        h = Hierarchy(DIMENSION_NAME, HIERARCHY_NAME)
        h.add_element('Total Years', 'Consolidated')
        h.add_element('All Consolidations', 'Consolidated')
        h.add_edge("All Consolidations", "Total Years", 1)
        for year in cls.years:
            h.add_element(year, 'Numeric')
            h.add_edge('Total Years', year, 1)
        for attribute in cls.attributes:
            h.add_element_attribute(attribute, "String")
        d.add_hierarchy(h)
        cls.tm1.dimensions.create(d)

        # write one element attribute value
        cls.tm1.cubes.cells.write_value('1988', '}ElementAttributes_' + DIMENSION_NAME, ('1989', 'Previous Year'))

    @classmethod
    def tearDown(cls):
        cls.tm1.dimensions.delete(DIMENSION_NAME)

    @classmethod
    def teardown_class(cls):
        cls.tm1.logout()

    def test_create_and_delete_element(self):
        element = Element(self.extra_year, "String")
        self.tm1.dimensions.hierarchies.elements.create(
            DIMENSION_NAME,
            HIERARCHY_NAME,
            element)

        element_returned = self.tm1.dimensions.hierarchies.elements.get(
            DIMENSION_NAME,
            HIERARCHY_NAME,
            element.name)
        self.assertEqual(element, element_returned)

        self.tm1.dimensions.hierarchies.elements.delete(
            DIMENSION_NAME,
            HIERARCHY_NAME,
            element.name)

    def test_get_element(self):
        for element_name in self.years:
            element = self.tm1.dimensions.hierarchies.elements.get(
                DIMENSION_NAME,
                HIERARCHY_NAME,
                element_name)
            self.assertEqual(element.name, element_name)

    def test_update_element(self):
        element = Element(self.extra_year, "S T R I N G")
        self.tm1.dimensions.hierarchies.elements.create(
            DIMENSION_NAME,
            HIERARCHY_NAME,
            element)

        element_name = self.extra_year
        element = self.tm1.dimensions.hierarchies.elements.get(DIMENSION_NAME, HIERARCHY_NAME, element_name)
        element.element_type = "Numeric"
        self.tm1.dimensions.hierarchies.elements.update(DIMENSION_NAME, HIERARCHY_NAME, element)

        element = self.tm1.dimensions.hierarchies.elements.get(DIMENSION_NAME, HIERARCHY_NAME, element_name)
        self.assertTrue(element.element_type == "Numeric")

        self.tm1.dimensions.hierarchies.elements.delete(
            DIMENSION_NAME,
            HIERARCHY_NAME,
            element.name)

    def test_get_element_attributes(self):
        element_attributes = self.tm1.dimensions.hierarchies.elements.get_element_attributes(
            DIMENSION_NAME,
            HIERARCHY_NAME)
        self.assertIn('Previous Year', element_attributes)
        self.assertIn('Next Year', element_attributes)

    def test_get_elements_filtered_by_attribute(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_attribute(
            DIMENSION_NAME,
            HIERARCHY_NAME,
            'Previous Year',
            '1988')
        self.assertIn('1989', elements)

    def test_create_filter_and_delete_element_attribute(self):
        attribute = ElementAttribute('Leap Year', 'Numeric')
        self.tm1.dimensions.hierarchies.elements.create_element_attribute(
            DIMENSION_NAME,
            HIERARCHY_NAME, attribute)
        # write one element attribute value
        self.tm1.cubes.cells.write_value(
            1,
            '}ElementAttributes_' + DIMENSION_NAME,
            ('1992', 'Leap Year'))
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_attribute(
            DIMENSION_NAME,
            HIERARCHY_NAME,
            'Leap Year', 1)
        self.assertIn('1992', elements)
        self.assertEqual(len(elements), 1)

        self.tm1.dimensions.hierarchies.elements.delete_element_attribute(
            DIMENSION_NAME,
            HIERARCHY_NAME,
            "Leap Year")

    def test_get_elements(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_elements(
            DIMENSION_NAME,
            HIERARCHY_NAME)
        element_names = [element.name for element in elements]
        for year in self.years:
            self.assertIn(year, element_names)
        self.assertNotIn(self.extra_year, element_names)

    def test_get_element_names(self):
        element_names = self.tm1.dimensions.hierarchies.elements.get_element_names(
            DIMENSION_NAME,
            HIERARCHY_NAME)
        for year in self.years:
            self.assertIn(year, element_names)

    def test_get_leaf_element_names(self):
        leaf_element_names = self.tm1.dimensions.hierarchies.elements.get_leaf_element_names(
            DIMENSION_NAME,
            HIERARCHY_NAME)
        for leaf in leaf_element_names:
            self.assertIn(leaf, self.years)
        self.assertNotIn(self.extra_year, leaf_element_names)
        self.assertNotIn("Total Years", leaf_element_names)

    def test_get_leaf_elements(self):
        leaf_elements = self.tm1.dimensions.hierarchies.elements.get_leaf_elements(
            DIMENSION_NAME,
            HIERARCHY_NAME)
        for leaf in leaf_elements:
            self.assertIn(leaf.name, self.years)
            self.assertNotEqual(leaf.element_type, "Consolidated")
        leaf_element_names = [element.name for element in leaf_elements]
        self.assertNotIn(self.extra_year, leaf_element_names)
        self.assertNotIn("Total Year", leaf_element_names)

    def test_element_exists(self):
        for year in self.years:
            self.assertTrue(self.tm1.dimensions.hierarchies.elements.exists(
                DIMENSION_NAME,
                HIERARCHY_NAME,
                year))

    def test_get_leaves_under_consolidation(self):
        leaves = self.tm1.dimensions.hierarchies.elements.get_leaves_under_consolidation(
            DIMENSION_NAME,
            HIERARCHY_NAME,
            "All Consolidations")
        self.assertNotIn("Total Years", leaves)
        for year in self.years:
            self.assertIn(year, leaves)

    def test_get_members_under_consolidation(self):
        leaves = self.tm1.dimensions.hierarchies.elements.get_members_under_consolidation(
            DIMENSION_NAME,
            HIERARCHY_NAME,
            "All Consolidations",
            leaves_only=True)
        self.assertNotIn("Total Years", leaves)
        for year in self.years:
            self.assertIn(year, leaves)

        members = self.tm1.dimensions.hierarchies.elements.get_members_under_consolidation(
            DIMENSION_NAME,
            HIERARCHY_NAME,
            "All Consolidations",
            leaves_only=False)
        self.assertIn("Total Years", members)
        for year in self.years:
            self.assertIn(year, members)


if __name__ == '__main__':
    unittest.main()

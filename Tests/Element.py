import unittest
import uuid
import os
import configparser

from TM1py.Objects import Dimension, Hierarchy, Element, ElementAttribute
from TM1py.Services import TM1Service

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))


dimension_prefix = 'TM1py_unittest_element_{}'


class TestElementMethods(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        # hard coded stuff
        cls.dimension_name = dimension_prefix.format(uuid.uuid4())
        cls.hierarchy_name = cls.dimension_name

        # Connection to TM1
        cls.tm1 = TM1Service(**config['tm1srv01'])

        # Elements
        cls.years = ("No Year", "1989", "1990", "1991", "1992")
        cls.extra_year = "4321"
        # Element Attributes
        cls.attributes = ('Previous Year', 'Next Year')

        # create dimension with a default hierarchy
        d = Dimension(cls.dimension_name)
        h = Hierarchy(cls.dimension_name, cls.hierarchy_name)
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
        cls.tm1.cubes.cells.write_value('1988', '}ElementAttributes_' + cls.dimension_name, ('1989', 'Previous Year'))

    def test01_create_element(self):
        element = Element(self.extra_year, "String")
        self.tm1.dimensions.hierarchies.elements.create(self.dimension_name, self.hierarchy_name, element)

    def test02_get_element(self):
        element_name = self.years[0]
        element = self.tm1.dimensions.hierarchies.elements.get(self.dimension_name, self.hierarchy_name, element_name)
        self.assertTrue(element.name == element_name)

    def test03_update_element(self):
        element_name = self.extra_year
        element = self.tm1.dimensions.hierarchies.elements.get(self.dimension_name, self.hierarchy_name, element_name)
        element.element_type = "Numeric"
        self.tm1.dimensions.hierarchies.elements.update(self.dimension_name, self.hierarchy_name, element)

        element = self.tm1.dimensions.hierarchies.elements.get(self.dimension_name, self.hierarchy_name, element_name)
        self.assertTrue(element.element_type == "Numeric")

    def test04_delete_element(self):
        element_name = self.extra_year
        self.tm1.dimensions.hierarchies.elements.delete(self.dimension_name, self.hierarchy_name, element_name)
        self.assertFalse(self.tm1.dimensions.hierarchies.elements.exists(self.dimension_name,
                                                                         self.hierarchy_name, element_name))

    def test05_get_element_attributes(self):
        element_attributes = self.tm1.dimensions.hierarchies.elements.get_element_attributes(self.dimension_name,
                                                                                             self.hierarchy_name)
        self.assertIn('Previous Year', element_attributes)
        self.assertIn('Next Year', element_attributes)

    def test06_get_elements_filtered_by_attribute(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_attribute(self.dimension_name,
                                                                                               self.hierarchy_name,
                                                                                               'Previous Year',
                                                                                               '1988')
        self.assertIn('1989', elements)

    def test07_create_element_attribute(self):
        attribute = ElementAttribute('Leap Year', 'Numeric')
        self.tm1.dimensions.hierarchies.elements.create_element_attribute(self.dimension_name,
                                                                          self.hierarchy_name, attribute)

        # write one element attribute value
        self.tm1.cubes.cells.write_value(1, '}ElementAttributes_' + self.dimension_name, ('1992', 'Leap Year'))
        elements = self.tm1.dimensions.hierarchies.elements.get_elements_filtered_by_attribute(self.dimension_name,
                                                                                               self.hierarchy_name,
                                                                                               'Leap Year', 1)
        self.assertIn('1992', elements)
        self.assertNotIn('1989', elements)

    def test08_get_element_names(self):
        elements = self.tm1.dimensions.hierarchies.elements.get_element_names(self.dimension_name, self.hierarchy_name)
        for year in self.years:
            self.assertIn(year, elements)

    def test09_delete_element_attribute(self):
        self.tm1.dimensions.hierarchies.elements.delete_element_attribute(self.dimension_name,
                                                                          self.hierarchy_name, "Leap Year")

    def test10_element_exists(self):
        for year in self.years:
            self.tm1.dimensions.hierarchies.elements.exists(self.dimension_name, self.hierarchy_name, year)

    def test11_get_leaves_under_consolidation(self):
        leaves = self.tm1.dimensions.hierarchies.elements.get_leaves_under_consolidation(self.dimension_name,
                                                                                         self.hierarchy_name,
                                                                                         "All Consolidations")
        self.assertNotIn("Total Years", leaves)
        for year in self.years:
            self.assertIn(year, leaves)

    def test12_get_members_under_consolidation(self):
        leaves = self.tm1.dimensions.hierarchies.elements.get_members_under_consolidation(self.dimension_name,
                                                                                          self.hierarchy_name,
                                                                                          "All Consolidations",
                                                                                          leaves_only=True)
        self.assertNotIn("Total Years", leaves)
        for year in self.years:
            self.assertIn(year, leaves)

        members = self.tm1.dimensions.hierarchies.elements.get_members_under_consolidation(self.dimension_name,
                                                                                           self.hierarchy_name,
                                                                                           "All Consolidations",
                                                                                           leaves_only=False)
        self.assertIn("Total Years", members)
        for year in self.years:
            self.assertIn(year, members)

    @classmethod
    def teardown_class(cls):
        cls.tm1.dimensions.delete(cls.dimension_name)
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()


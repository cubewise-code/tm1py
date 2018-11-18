import configparser
import os
import unittest
import uuid

from TM1py.Objects import Dimension, Hierarchy, Element
from TM1py.Objects import ElementAttribute
from TM1py.Services import TM1Service

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))

PREFIX = "TM1py_Tests_Dimension_"
DIMENSION_NAME = PREFIX + "Some_Dimension"
HIERARCHY_NAME = DIMENSION_NAME


class TestDimensionMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])

    @classmethod
    def setUp(cls):
        cls.create_dimension()

    @classmethod
    def tearDown(cls):
        cls.delete_dimension()

    @classmethod
    def create_dimension(cls):
        root_element = Element(name='Root', element_type='Consolidated')
        elements = [root_element]
        edges = {}
        for i in range(1000):
            element_name = str(uuid.uuid4())
            elements.append(Element(name=element_name, element_type='Numeric'))
            edges[('Root', element_name)] = i
        element_attributes = [
            ElementAttribute(name='Name Long', attribute_type='Alias'),
            ElementAttribute(name='Name Short', attribute_type='Alias')]
        h = Hierarchy(
            name=DIMENSION_NAME,
            dimension_name=DIMENSION_NAME,
            elements=elements,
            edges=edges,
            element_attributes=element_attributes)
        d = Dimension(name=DIMENSION_NAME, hierarchies=[h])
        cls.tm1.dimensions.create(d)

    @classmethod
    def delete_dimension(cls):
        cls.tm1.dimensions.delete(DIMENSION_NAME)

    def test_get_dimension(self):
        # get it
        d = self.tm1.dimensions.get(dimension_name=DIMENSION_NAME)
        h = d.hierarchies[0]
        self.assertIsInstance(h, Hierarchy)

    def test_update_dimension(self):
        # get dimension from tm1
        d = self.tm1.dimensions.get(dimension_name=DIMENSION_NAME)
        # create element objects
        elements = [Element(name='e1', element_type='Consolidated'),
                    Element(name='e2', element_type='Numeric'),
                    Element(name='e3', element_type='Numeric'),
                    Element(name='e4', element_type='Numeric')]
        # create edge objects
        edges = {
            ('e1', 'e2'): 1,
            ('e1', 'e3'): 1,
            ('e1', 'e4'): 1}
        # create the element_attributes objects
        element_attributes = [ElementAttribute(name='Name Long', attribute_type='Alias'),
                              ElementAttribute(name='Name Short', attribute_type='Alias'),
                              ElementAttribute(name='Currency', attribute_type='String')]
        # create hierarchy object
        hierarchy = Hierarchy(name=DIMENSION_NAME, dimension_name=DIMENSION_NAME, elements=elements,
                              element_attributes=element_attributes, edges=edges)

        # replace existing hierarchy with new hierarchy
        d.remove_hierarchy(DIMENSION_NAME)
        d.add_hierarchy(hierarchy)

        # update dimension in TM1
        self.tm1.dimensions.update(d)

        # Test
        dimension = self.tm1.dimensions.get(DIMENSION_NAME)
        self.assertEqual(len(dimension.hierarchies[0].elements), len(elements))

    def test_get_all_names(self):
        self.assertIn(DIMENSION_NAME, self.tm1.dimensions.get_all_names())

    def test_execute_mdx(self):
        mdx = "{TM1SubsetAll(" + DIMENSION_NAME + ")}"
        elements = self.tm1.dimensions.execute_mdx(DIMENSION_NAME, mdx)
        self.assertTrue(len(elements) > 0)

    def test_rename_dimension(self):
        original_dimension_name = PREFIX + "Original_Dimension"
        renamed_dimension_name = PREFIX + "Renamed_Dimension"

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
            dimension_name=original_dimension_name,
            hierarchy_name=original_dimension_name)
        summary2 = self.tm1.dimensions.hierarchies.get_hierarchy_summary(
            dimension_name=renamed_dimension_name,
            hierarchy_name=renamed_dimension_name)
        self.assertEqual(summary1, summary2)

        # delete
        for dim_name in (original_dimension_name, renamed_dimension_name):
            self.tm1.dimensions.delete(dimension_name=dim_name)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()

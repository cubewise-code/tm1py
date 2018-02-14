import unittest
import uuid

from TM1py.Objects import Dimension, Hierarchy, Element
from TM1py.Objects import ElementAttribute
from TM1py.Services import TM1Service

from .config import test_config


class TestDimensionMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tm1 = TM1Service(**test_config)
        cls.dimension_name = 'TM1py_unittest_dimension_{}'.format(int(uuid.uuid4()))
        cls.hierarchy_name = cls.dimension_name

    def test1_create_dimension(self):
        root_element = Element(name='Root', element_type='Consolidated')
        elements = [root_element]
        edges = {}
        for i in range(1000):
            element_name = str(uuid.uuid4())
            elements.append(Element(name=element_name, element_type='Numeric'))
            edges[('Root', element_name)] = i
        element_attributes = [ElementAttribute(name='Name Long', attribute_type='Alias'),
                              ElementAttribute(name='Name Short', attribute_type='Alias')]
        h = Hierarchy(name=self.dimension_name, dimension_name=self.dimension_name,
                      elements=elements, edges=edges, element_attributes=element_attributes)
        d = Dimension(name=self.dimension_name, hierarchies=[h])
        self.tm1.dimensions.create(d)

        # Test
        dimensions = self.tm1.dimensions.get_all_names()
        self.assertIn(self.dimension_name, dimensions)

        # Get it
        d = self.tm1.dimensions.get(dimension_name=self.dimension_name)
        h = d.hierarchies[0]
        # Test
        self.assertEqual(len(h.elements), 1001)
        self.assertEqual(len(h.element_attributes), 2)

    def test2_get_dimension(self):
        # get it
        d = self.tm1.dimensions.get(dimension_name=self.dimension_name)
        h = d.hierarchies[0]
        self.assertIsInstance(h, Hierarchy)

    def test3_update_dimension(self):
        # get dimension from tm1
        d = self.tm1.dimensions.get(dimension_name=self.dimension_name)
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
        hierarchy = Hierarchy(name=self.dimension_name, dimension_name=self.dimension_name, elements=elements,
                              element_attributes=element_attributes, edges=edges)

        # replace existing hierarchy with new hierarchy
        d.remove_hierarchy(self.dimension_name)
        d.add_hierarchy(hierarchy)

        # update dimension in TM1
        self.tm1.dimensions.update(d)

        # Test
        dimension = self.tm1.dimensions.get(self.dimension_name)
        self.assertEqual(len(dimension.hierarchies[0].elements), len(elements))

    def test4_get_all_names(self):
        self.assertIn(self.dimension_name, self.tm1.dimensions.get_all_names())

    def test5_execute_mdx(self):
        mdx = "{TM1SubsetAll(" + self.dimension_name + ")}"
        elements = self.tm1.dimensions.execute_mdx(self.dimension_name, mdx)
        self.assertTrue(len(elements) > 0)

    def test6_delete_dimension(self):
        dimensions_before = self.tm1.dimensions.get_all_names()
        self.tm1.dimensions.delete(self.dimension_name)
        dimensions_after = self.tm1.dimensions.get_all_names()

        # Test
        self.assertIn(self.dimension_name, dimensions_before)
        self.assertNotIn(self.dimension_name, dimensions_after)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()



if __name__ == '__main__':
    unittest.main()

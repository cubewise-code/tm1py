from TM1py import TM1pyQueries as TM1, TM1pyLogin, Dimension, Hierarchy, Element, Edge, ElementAttribute
import uuid
import unittest


class TestDimensionMethods(unittest.TestCase):
    login = TM1pyLogin.native('admin', 'apple')
    tm1 = TM1(ip='', port=8001, login=login, ssl=False)

    dimension_name = 'TM1py_unittest_dimension_{}'.format(int(uuid.uuid4()))
    hierarchy_name = dimension_name

    def test1_create_dimension(self):
        root_element = Element(name='Root', element_type='Consolidated')
        elements = [root_element]
        edges = []
        for i in range(1000):
            element_name = str(uuid.uuid4())
            elements.append(Element(name=element_name, element_type='Numeric'))
            edges.append(Edge(parent_name='Root', component_name=element_name, weight=i))
        h = Hierarchy(name=self.dimension_name, dimension_name=self.dimension_name, elements=elements, edges=edges)
        d = Dimension(name=self.dimension_name, hierarchies=[h])
        # create it
        self.tm1.create_dimension(d)

        # Test
        dimensions = self.tm1.get_all_dimension_names()
        self.assertIn(self.dimension_name, dimensions)


    def test2_get_dimension(self):
        # get it
        d = self.tm1.get_dimension(dimension_name=self.dimension_name)

        # Test
        self.assertEqual(len(d.hierarchies[0].elements), 1001)


    def test3_update_dimension(self):
        # get dimension from tm1
        d = self.tm1.get_dimension(dimension_name=self.dimension_name)
        # create element objects
        elements = [Element(name='e1', element_type='Consolidated'),
                    Element(name='e2', element_type='Numeric'),
                    Element(name='e3', element_type='Numeric'),
                    Element(name='e4', element_type='Numeric')]
        # create edge objects
        edges = [Edge(parent_name='e1', component_name='e2', weight=1),
                 Edge(parent_name='e1', component_name='e3', weight=1),
                 Edge(parent_name='e1', component_name='e4', weight=1)]
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
        self.tm1.update_dimension(d)

        # Test
        dimension = self.tm1.get_dimension(self.dimension_name)
        self.assertEqual(len(dimension.hierarchies[0].elements), len(elements))


    def test4_delete_dimension(self):
        dimensions_before = self.tm1.get_all_dimension_names()
        self.tm1.delete_dimension(self.dimension_name)
        dimensions_after = self.tm1.get_all_dimension_names()

        # Test
        self.assertIn(self.dimension_name,dimensions_before)
        self.assertNotIn(self.dimension_name, dimensions_after)

if __name__ == '__main__':
    unittest.main()

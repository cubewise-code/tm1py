import uuid
import unittest

from Services.RESTService import RESTService
from Services.LoginService import LoginService
from Services.DimensionService import DimensionService
from Objects.Dimension import Dimension
from Objects.Hierarchy import Hierarchy
from Objects.Element import Element
from Objects.ElementAttribute import ElementAttribute


# Configuration for tests
port = 8001
user = 'admin'
pwd = 'apple'


class TestDimensionMethods(unittest.TestCase):
    login = LoginService.native(user, pwd)
    tm1_rest = RESTService(ip='', port=port, login=login, ssl=False)

    dimension_service = DimensionService(tm1_rest)

    dimension_name = 'TM1py_unittest_dimension_{}'.format(int(uuid.uuid4()))
    hierarchy_name = dimension_name

    def test1_create_dimension(self):
        root_element = Element(name='Root', element_type='Consolidated')
        elements = [root_element]
        edges = {}
        for i in range(1000):
            element_name = str(uuid.uuid4())
            elements.append(Element(name=element_name, element_type='Numeric'))
            edges[('Root', element_name)] = i
        h = Hierarchy(name=self.dimension_name, dimension_name=self.dimension_name, elements=elements, edges=edges)
        d = Dimension(name=self.dimension_name, hierarchies=[h])
        # create it
        self.dimension_service.create(d)

        # Test
        dimensions = self.dimension_service.get_all_names()
        self.assertIn(self.dimension_name, dimensions)

    def test2_get_dimension(self):
        # get it
        d = self.dimension_service.get(dimension_name=self.dimension_name)
        # Test
        self.assertEqual(len(d.hierarchies[0].elements), 1001)

    def test3_update_dimension(self):
        # get dimension from tm1
        d = self.dimension_service.get(dimension_name=self.dimension_name)
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
        self.dimension_service.update(d)

        # Test
        dimension = self.dimension_service.get(self.dimension_name)
        self.assertEqual(len(dimension.hierarchies[0].elements), len(elements))

    def test4_delete_dimension(self):
        dimensions_before = self.dimension_service.get_all_names()
        self.dimension_service.delete(self.dimension_name)
        dimensions_after = self.dimension_service.get_all_names()

        # Test
        self.assertIn(self.dimension_name,dimensions_before)
        self.assertNotIn(self.dimension_name, dimensions_after)

    def test5_logout(self):
        self.tm1_rest.logout()

if __name__ == '__main__':
    unittest.main()

from TM1py import TM1pyQueries as TM1, TM1pyLogin, Dimension, Hierarchy, Element, Edge
import uuid
import unittest


class TestCubeMethods(unittest.TestCase):
    login = TM1pyLogin.native('admin', 'apple')
    tm1 = TM1(ip='', port=8001, login=login, ssl=False)

    dimension_name = 'TM1py_unittest_dimension_{}'.format(int(uuid.uuid4()))
    hierarchy_name = dimension_name
    element_name = 'TM1py_unittest_element_{}'.format(int(uuid.uuid4()))

    def test1_create_dimension(self):
        e = Element(name=self.element_name, element_type='Consolidated', attributes=['attr1', 'attr2'])
        h = Hierarchy(name=self.dimension_name,dimension_name=self.dimension_name,elements=[e])
        d = Dimension(name=self.dimension_name, hierarchies= [h])

        self.tm1.create_dimension(d)


    def test2_get_dimension(self):
        pass


    def test3_update_dimension(self):
        pass


    def test4_delete_dimension(self):
        pass

    def test5_logout(self):
        self.tm1.logout()


if __name__ == '__main__':
    unittest.main()

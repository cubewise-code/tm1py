import random
import unittest
import uuid
import os
import configparser

from TM1py.Objects import Dimension, Hierarchy, Subset, ElementAttribute, Element
from TM1py.Services import TM1Service

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))


class TestSubsetMethods(unittest.TestCase):

    # Check if Dimensions exists. If not create it
    @classmethod
    def setup_class(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])

        # Define Names
        cls.prefix = 'TM1py_unittest_dimension_'
        cls.dimension_name = cls.prefix + str(uuid.uuid4())
        cls.subset_name_static = cls.prefix + "static"
        cls.subset_name_dynamic = cls.prefix + "dynamic"

        # Instantiate Subsets
        cls.static_subset = Subset(dimension_name=cls.dimension_name,
                                   subset_name=cls.subset_name_static,
                                   elements=['USD', 'EUR', 'NZD', 'Dum\'my'])
        cls.dynamic_subset = Subset(dimension_name=cls.dimension_name,
                                    subset_name=cls.subset_name_dynamic,
                                    expression='{ HIERARCHIZE( {TM1SUBSETALL( [' + cls.dimension_name + '] )} ) }')

        elements = [Element('USD', 'Numeric'),
                    Element('EUR', 'Numeric'),
                    Element('JPY', 'Numeric'),
                    Element('CNY', 'Numeric'),
                    Element('GBP', 'Numeric'),
                    Element('NZD', 'Numeric'),
                    Element('Dum\'my', 'Numeric')]
        element_attributes = [ElementAttribute('Currency Name', 'String')]
        h = Hierarchy(cls.dimension_name, cls.dimension_name, elements, element_attributes)
        d = Dimension(cls.dimension_name, hierarchies=[h])
        cls.tm1.dimensions.create(d)

    # 1. Create subset
    def test_1create_subset(self):
        for private in (True, False):
            self.tm1.dimensions.subsets.create(self.static_subset, private=private)
            self.tm1.dimensions.hierarchies.subsets.create(self.dynamic_subset, private=private)

    # 2. Get subset
    def test_2get_subset(self):
        for private in (True, False):
            s = self.tm1.dimensions.hierarchies.subsets.get(dimension_name=self.dimension_name,
                                                            subset_name=self.subset_name_static,
                                                            private=private)
            self.assertEqual(self.static_subset, s)
            s = self.tm1.dimensions.hierarchies.subsets.get(dimension_name=self.dimension_name,
                                                            subset_name=self.subset_name_dynamic,
                                                            private=private)
            self.assertEqual(self.dynamic_subset, s)

    # 3. Update subset
    def test_3update_subset(self):
        for private in (True, False):
            # Get static subset
            s = self.tm1.dimensions.hierarchies.subsets.get(dimension_name=self.dimension_name,
                                                            subset_name=self.subset_name_static,
                                                            private=private)
            # Check before update
            self.assertEqual(self.static_subset, s)

            s.add_elements(['NZD'])
            # Update it
            self.tm1.dimensions.hierarchies.subsets.update(s, private=private)
            # Get it again
            s = self.tm1.dimensions.hierarchies.subsets.get(dimension_name=self.dimension_name,
                                                            subset_name=self.subset_name_static,
                                                            private=private)
            # Check after update
            self.assertEquals(len(s.elements), 5)
            self.assertNotEqual(self.static_subset, s)

            # Get dynamic subset
            s = self.tm1.dimensions.hierarchies.subsets.get(dimension_name=self.dimension_name,
                                                            subset_name=self.subset_name_dynamic,
                                                            private=private)
            # Check before update
            self.assertEqual(self.dynamic_subset, s)

            s.expression = '{{ [{}].[EUR], [{}].[USD] }})'.format(self.dimension_name, self.dimension_name)
            # Update it
            self.tm1.dimensions.hierarchies.subsets.update(subset=s, private=private)
            # Get it again
            s = self.tm1.dimensions.hierarchies.subsets.get(dimension_name=self.dimension_name,
                                                            subset_name=self.subset_name_dynamic,
                                                            private=private)
            # Check after update
            self.assertEquals(s.expression,
                              '{{ [{}].[EUR], [{}].[USD] }})'.format(self.dimension_name, self.dimension_name))

            self.assertNotEqual(self.dynamic_subset, s)

    # 4. get all names
    def test_4get_all_names(self):
        for private in (True, False):
            subset_names = self.tm1.dimensions.subsets.get_all_names(dimension_name=self.dimension_name,
                                                                     hierarchy_name=self.dimension_name,
                                                                     private=private)
            self.assertIn(self.subset_name_dynamic, subset_names)
            self.assertIn(self.subset_name_static, subset_names)

    def test_5delete_subset(self):
        for private in (True, False):
            self.tm1.dimensions.hierarchies.subsets.delete(dimension_name=self.dimension_name,
                                                           subset_name=self.subset_name_static,
                                                           private=private)
            self.tm1.dimensions.hierarchies.subsets.delete(dimension_name=self.dimension_name,
                                                           subset_name=self.subset_name_dynamic,
                                                           private=private)

    @classmethod
    def teardown_class(cls):
        cls.tm1.dimensions.delete(cls.dimension_name)
        cls.tm1.logout()

if __name__ == '__main__':
    unittest.main()

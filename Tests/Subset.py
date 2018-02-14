import random
import unittest
import uuid

from TM1py.Objects import Dimension, Hierarchy, Subset, ElementAttribute, Element
from TM1py.Services import TM1Service

from .config import test_config


class TestSubsetMethods(unittest.TestCase):

    # Check if Dimensions exists. If not create it
    @classmethod
    def setup_class(cls):
        cls.tm1 = TM1Service(**test_config)

        # Do random stuff
        cls.private = bool(random.getrandbits(1))

        # Define Names
        cls.prefix = 'TM1py_unittest_dimension_'
        cls.dimension_name = cls.prefix + str(uuid.uuid4())
        cls.subset_name_static = cls.prefix + str(uuid.uuid4())
        cls.subset_name_dynamic = cls.prefix + str(uuid.uuid4())

        # Instantiate Subsets
        cls.static_subset = Subset(dimension_name=cls.dimension_name,
                                   subset_name=cls.subset_name_static,
                                   elements=['USD', 'EUR', 'NZD'])
        cls.dynamic_subset = Subset(dimension_name=cls.dimension_name,
                                    subset_name=cls.subset_name_dynamic,
                                    expression='{ HIERARCHIZE( {TM1SUBSETALL( [' + cls.dimension_name + '] )} ) }')

        elements = [Element('USD', 'Numeric'),
                    Element('EUR', 'Numeric'),
                    Element('JPY', 'Numeric'),
                    Element('CNY', 'Numeric'),
                    Element('GBP', 'Numeric'),
                    Element('NZD', 'Numeric')]
        element_attributes = [ElementAttribute('Currency Name', 'String')]
        h = Hierarchy(cls.dimension_name, cls.dimension_name, elements, element_attributes)
        d = Dimension(cls.dimension_name, hierarchies=[h])
        cls.tm1.dimensions.create(d)

    # 1. Create subset
    def test_1create_subset(self):
        print(self.static_subset.name)
        print(self.dynamic_subset.name)
        self.tm1.dimensions.subsets.create(self.static_subset, private=self.private)
        self.tm1.dimensions.hierarchies.subsets.create(self.dynamic_subset, private=self.private)

    # 2. Get subset
    def test_2get_subset(self):
        s = self.tm1.dimensions.hierarchies.subsets.get(dimension_name=self.dimension_name,
                                                        subset_name=self.subset_name_static,
                                                        private=self.private)
        self.assertEqual(self.static_subset.body, s.body)
        s = self.tm1.dimensions.hierarchies.subsets.get(dimension_name=self.dimension_name,
                                                        subset_name=self.subset_name_dynamic,
                                                        private=self.private)
        self.assertEqual(self.dynamic_subset.body, s.body)

    # 3. Update subset
    def test_3update_subset(self):
        s = self.tm1.dimensions.hierarchies.subsets.get(dimension_name=self.dimension_name,
                                                        subset_name=self.subset_name_static,
                                                        private=self.private)
        s.add_elements(['NZD'])
        # Update it
        self.tm1.dimensions.hierarchies.subsets.update(s, private=self.private)
        # Get it again
        s = self.tm1.dimensions.hierarchies.subsets.get(dimension_name=self.dimension_name,
                                                        subset_name=self.subset_name_static,
                                                        private=self.private)
        # Test it !
        self.assertEquals(len(s.elements), 4)
        # Get subset
        s = self.tm1.dimensions.hierarchies.subsets.get(dimension_name=self.dimension_name,
                                                        subset_name=self.subset_name_dynamic,
                                                        private=self.private)

        s.expression = '{{ [{}].[EUR], [{}].[USD] }})'.format(self.dimension_name, self.dimension_name)
        # Update it
        self.tm1.dimensions.hierarchies.subsets.update(subset=s, private=self.private)
        # Get it again
        s = self.tm1.dimensions.hierarchies.subsets.get(dimension_name=self.dimension_name,
                                                        subset_name=self.subset_name_dynamic,
                                                        private=self.private)
        # Test it !
        self.assertEquals(s.expression,
                          '{{ [{}].[EUR], [{}].[USD] }})'.format(self.dimension_name, self.dimension_name))

    def test_4get_all_names(self):
        subset_names = self.tm1.dimensions.subsets.get_all_names(dimension_name=self.dimension_name,
                                                                 hierarchy_name=self.dimension_name,
                                                                 private=self.private)
        self.assertIn(self.subset_name_dynamic, subset_names)
        self.assertIn(self.subset_name_static, subset_names)

    # 4. Delete subsets
    def test_5delete_subset(self):
        self.tm1.dimensions.hierarchies.subsets.delete(dimension_name=self.dimension_name,
                                                       subset_name=self.subset_name_static,
                                                       private=self.private)
        self.tm1.dimensions.hierarchies.subsets.delete(dimension_name=self.dimension_name,
                                                       subset_name=self.subset_name_dynamic,
                                                       private=self.private)

    @classmethod
    def teardown_class(cls):
        cls.tm1.dimensions.delete(cls.dimension_name)
        cls.tm1.logout()

if __name__ == '__main__':
    unittest.main()

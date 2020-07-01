import configparser
import unittest
from pathlib import Path

from TM1py.Objects import Dimension, Hierarchy, Subset, ElementAttribute, Element
from TM1py.Services import TM1Service

config = configparser.ConfigParser()
config.read(Path(__file__).parent.joinpath('config.ini'))

PREFIX = "TM1py_Tests_Subset_"


class TestSubsetMethods(unittest.TestCase):
    tm1 = None

    # Check if Dimensions exists. If not create it
    @classmethod
    def setup_class(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])

        # Define Names
        cls.dimension_name = PREFIX + "Dimension"
        cls.subset_name_static = PREFIX + "static"
        cls.subset_name_dynamic = PREFIX + "dynamic"

    def setUp(self):
        # Instantiate Subsets
        self.static_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_static,
            elements=['USD', 'EUR', 'NZD', 'Dum\'my'])
        self.dynamic_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_dynamic,
            expression='{ HIERARCHIZE( {TM1SUBSETALL( [' + self.dimension_name + '] )} ) }')

        elements = [Element('USD', 'Numeric'),
                    Element('EUR', 'Numeric'),
                    Element('JPY', 'Numeric'),
                    Element('CNY', 'Numeric'),
                    Element('GBP', 'Numeric'),
                    Element('NZD', 'Numeric'),
                    Element('Dum\'my', 'Numeric')]
        element_attributes = [ElementAttribute('Currency Name', 'String')]
        h = Hierarchy(self.dimension_name, self.dimension_name, elements, element_attributes)
        d = Dimension(self.dimension_name, hierarchies=[h])
        self.tm1.dimensions.create(d)

        for private in (True, False):
            self.tm1.dimensions.subsets.create(
                subset=self.static_subset,
                private=private)
            self.tm1.dimensions.subsets.create(
                subset=self.dynamic_subset,
                private=private)

    def tearDown(self):
        self.tm1.dimensions.delete(self.dimension_name)

    def test_is_dynamic(self):
        subset = self.tm1.dimensions.subsets.get(
            subset_name=self.dynamic_subset.name,
            dimension_name=self.dynamic_subset.dimension_name,
            private=False)
        self.assertTrue(subset.is_dynamic)
        self.assertFalse(subset.is_static)

    def test_is_static(self):
        subset = self.tm1.dimensions.subsets.get(
            subset_name=self.static_subset.name,
            dimension_name=self.static_subset.dimension_name,
            private=False)
        self.assertTrue(subset.is_static)
        self.assertFalse(subset.is_dynamic)

    def test_create_and_delete_subset_static_private(self):
        private = True
        static_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name="subset1",
            elements=['USD', 'EUR', 'NZD', 'Dum\'my'])

        response = self.tm1.dimensions.subsets.create(
            subset=static_subset,
            private=private)
        self.assertTrue(response.ok)

        response = self.tm1.dimensions.hierarchies.subsets.delete(
            dimension_name=self.dimension_name,
            subset_name=static_subset.name,
            private=private)
        self.assertTrue(response.ok)

    def test_create_and_delete_subset_dynamic_private(self):
        private = True
        dynamic_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name="subset2",
            expression='{ HIERARCHIZE( {TM1SUBSETALL( [' + self.dimension_name + '] )} ) }')

        response = self.tm1.dimensions.subsets.create(
            subset=dynamic_subset,
            private=private)
        self.assertTrue(response.ok)

        response = self.tm1.dimensions.hierarchies.subsets.delete(
            dimension_name=self.dimension_name,
            subset_name=dynamic_subset.name,
            private=private)
        self.assertTrue(response.ok)

    def test_create_and_delete_static_subset_public(self):
        private = False
        static_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name="subset1",
            elements=['USD', 'EUR', 'NZD', 'Dum\'my'])

        response = self.tm1.dimensions.subsets.create(
            subset=static_subset,
            private=private)
        self.assertTrue(response.ok)

        response = self.tm1.dimensions.hierarchies.subsets.delete(
            dimension_name=self.dimension_name,
            subset_name=static_subset.name,
            private=private)
        self.assertTrue(response.ok)

    def test_create_and_delete_dynamic_subset_public(self):
        private = False

        dynamic_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name="subset2",
            expression='{ HIERARCHIZE( {TM1SUBSETALL( [' + self.dimension_name + '] )} ) }')

        response = self.tm1.dimensions.subsets.create(
            subset=dynamic_subset,
            private=private)
        self.assertTrue(response.ok)

        response = self.tm1.dimensions.hierarchies.subsets.delete(
            dimension_name=self.dimension_name,
            subset_name=dynamic_subset.name,
            private=private)
        self.assertTrue(response.ok)

    def test_exists_private(self):
        private = True
        self.assertTrue(self.tm1.dimensions.subsets.exists(
            subset_name=self.static_subset.name,
            dimension_name=self.dimension_name,
            private=private
        ))
        self.assertTrue(self.tm1.dimensions.subsets.exists(
            subset_name=self.dynamic_subset.name,
            dimension_name=self.dimension_name,
            private=private
        ))
        self.assertFalse(self.tm1.dimensions.subsets.exists(
            subset_name="wrong",
            dimension_name=self.dimension_name,
            private=private
        ))

    def test_exists_public(self):
        private = False
        self.assertTrue(self.tm1.dimensions.subsets.exists(
            subset_name=self.static_subset.name,
            dimension_name=self.dimension_name,
            private=private
        ))
        self.assertTrue(self.tm1.dimensions.subsets.exists(
            subset_name=self.dynamic_subset.name,
            dimension_name=self.dimension_name,
            private=private
        ))
        self.assertFalse(self.tm1.dimensions.subsets.exists(
            subset_name="wrong",
            dimension_name=self.dimension_name,
            private=private
        ))

    def test_get_subset_private(self):
        private = True
        s = self.tm1.dimensions.hierarchies.subsets.get(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_static,
            private=private)
        self.assertEqual(self.static_subset, s)
        s = self.tm1.dimensions.hierarchies.subsets.get(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_dynamic,
            private=private)
        self.assertEqual(self.dynamic_subset, s)

    def test_get_subset_public(self):
        private = False
        s = self.tm1.dimensions.hierarchies.subsets.get(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_static,
            private=private)
        self.assertEqual(self.static_subset, s)
        s = self.tm1.dimensions.hierarchies.subsets.get(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_dynamic,
            private=private)
        self.assertEqual(self.dynamic_subset, s)

    def test_update_subset_static_private(self):
        private = True
        # Get static subset
        s = self.tm1.dimensions.hierarchies.subsets.get(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_static,
            private=private)
        # Check before update
        self.assertEqual(self.static_subset, s)

        s.add_elements(['NZD'])
        # Update it
        self.tm1.dimensions.hierarchies.subsets.update(s, private=private)
        # Get it again
        s = self.tm1.dimensions.hierarchies.subsets.get(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_static,
            private=private)
        # Check after update
        self.assertEquals(len(s.elements), 5)
        self.assertNotEqual(self.static_subset, s)

    def test_update_subset_dynamic_private(self):
        private = True
        # Get dynamic subset
        s = self.tm1.dimensions.hierarchies.subsets.get(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_dynamic,
            private=private)
        # Check before update
        self.assertEqual(self.dynamic_subset, s)

        s.expression = '{{ [{}].[EUR], [{}].[USD] }})'.format(
            self.dimension_name,
            self.dimension_name)
        # Update it
        self.tm1.dimensions.hierarchies.subsets.update(
            subset=s,
            private=private)
        # Get it again
        s = self.tm1.dimensions.hierarchies.subsets.get(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_dynamic,
            private=private)
        # Check after update
        self.assertEquals(
            s.expression,
            '{{ [{}].[EUR], [{}].[USD] }})'.format(self.dimension_name, self.dimension_name))

        self.assertNotEqual(self.dynamic_subset, s)

    def test_update_subset_static_public(self):
        private = False
        # Get static subset
        subset = self.tm1.dimensions.hierarchies.subsets.get(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_static,
            private=private)
        # Check before update
        self.assertEqual(self.static_subset, subset)

        subset.add_elements(['NZD'])
        # Update it
        self.tm1.dimensions.hierarchies.subsets.update(subset, private=private)
        # Get it again
        subset = self.tm1.dimensions.hierarchies.subsets.get(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_static,
            private=private)
        # Check after update
        self.assertEquals(len(subset.elements), 5)
        self.assertNotEqual(self.static_subset, subset)

    def test_update_subset_dynamic_public(self):
        private = False
        # Get dynamic subset
        subset = self.tm1.dimensions.hierarchies.subsets.get(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_dynamic,
            private=private)
        # Check before update
        self.assertEqual(self.dynamic_subset, subset)

        subset.expression = '{{ [{}].[EUR], [{}].[USD] }})'.format(
            self.dimension_name,
            self.dimension_name)
        # Update it
        self.tm1.dimensions.hierarchies.subsets.update(
            subset=subset,
            private=private)
        # Get it again
        subset = self.tm1.dimensions.hierarchies.subsets.get(
            dimension_name=self.dimension_name,
            subset_name=self.subset_name_dynamic,
            private=private)
        # Check after update
        self.assertEquals(
            subset.expression,
            '{{ [{}].[EUR], [{}].[USD] }})'.format(self.dimension_name, self.dimension_name))

        self.assertNotEqual(self.dynamic_subset, subset)
        
    def test_make_static_private(self):
        private = True
        subset = self.tm1.dimensions.subsets.get(
            subset_name=self.dynamic_subset.name,
            dimension_name=self.dynamic_subset.dimension_name,
            private=private)
        self.assertTrue(subset.is_dynamic)
        self.tm1.dimensions.hierarchies.subsets.make_static(
            subset_name=self.dynamic_subset.name,
            dimension_name=self.dynamic_subset.dimension_name,
            private=private)
        self.assertTrue(subset.is_static)
        
    def test_make_static_private(self):
        private = False
        subset = self.tm1.dimensions.subsets.get(
            subset_name=self.dynamic_subset.name,
            dimension_name=self.dynamic_subset.dimension_name,
            private=private)
        self.assertTrue(subset.is_dynamic)
        self.tm1.dimensions.hierarchies.subsets.make_static(
            subset_name=self.dynamic_subset.name,
            dimension_name=self.dynamic_subset.dimension_name,
            private=private)
        self.assertTrue(subset.is_static)

    def test_get_all_names_private(self):
        private = True
        subset_names = self.tm1.dimensions.subsets.get_all_names(
            dimension_name=self.dimension_name,
            hierarchy_name=self.dimension_name,
            private=private)
        self.assertIn(self.subset_name_dynamic, subset_names)
        self.assertIn(self.subset_name_static, subset_names)

    def test_get_all_names_public(self):
        private = False
        subset_names = self.tm1.dimensions.subsets.get_all_names(
            dimension_name=self.dimension_name,
            hierarchy_name=self.dimension_name,
            private=private)
        self.assertIn(self.subset_name_dynamic, subset_names)
        self.assertIn(self.subset_name_static, subset_names)

    def test_delete_elements_from_static_subset_public(self):
        private = False
        static_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name="subset1",
            elements=['USD', 'EUR', 'NZD', 'Dum\'my'])
        self.tm1.dimensions.subsets.create(
            subset=static_subset,
            private=private)
        subset = self.tm1.dimensions.subsets.get(
            dimension_name=static_subset.dimension_name,
            hierarchy_name=static_subset.hierarchy_name,
            subset_name=static_subset.name,
            private=private)
        self.assertEqual(len(subset.elements), 4)

        self.tm1.dimensions.subsets.delete_elements_from_static_subset(
            dimension_name=static_subset.dimension_name,
            hierarchy_name=static_subset.hierarchy_name,
            subset_name=static_subset.name,
            private=private)
        subset = self.tm1.dimensions.subsets.get(
            dimension_name=static_subset.dimension_name,
            hierarchy_name=static_subset.hierarchy_name,
            subset_name=static_subset.name,
            private=private)
        self.assertEqual(len(subset.elements), 0)

    def test_delete_elements_from_static_subset_private(self):
        private = True
        static_subset = Subset(
            dimension_name=self.dimension_name,
            subset_name="subset1",
            elements=['USD', 'EUR', 'NZD', 'Dum\'my'])
        self.tm1.dimensions.subsets.create(
            subset=static_subset,
            private=private)
        subset = self.tm1.dimensions.subsets.get(
            dimension_name=static_subset.dimension_name,
            hierarchy_name=static_subset.hierarchy_name,
            subset_name=static_subset.name,
            private=private)
        self.assertEqual(len(subset.elements), 4)

        self.tm1.dimensions.subsets.delete_elements_from_static_subset(
            dimension_name=static_subset.dimension_name,
            hierarchy_name=static_subset.hierarchy_name,
            subset_name=static_subset.name,
            private=private)
        subset = self.tm1.dimensions.subsets.get(
            dimension_name=static_subset.dimension_name,
            hierarchy_name=static_subset.hierarchy_name,
            subset_name=static_subset.name,
            private=private)
        self.assertEqual(len(subset.elements), 0)

    def test_get_element_names_static(self):
        element_names = self.tm1.subsets.get_element_names(
            self.dimension_name,
            self.dimension_name,
            self.subset_name_static,
            False)

        self.assertEqual(self.static_subset.elements, element_names)

    def test_get_element_names_dynamic(self):
        element_names = self.tm1.subsets.get_element_names(
            self.dimension_name,
            self.dimension_name,
            self.subset_name_dynamic,
            False)

        self.assertEqual(
            ['USD', 'EUR', 'JPY', 'CNY', 'GBP', 'NZD', "Dum'my"],
            element_names)

    @classmethod
    def teardown_class(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()

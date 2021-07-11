import unittest

from TM1py import Hierarchy


class TestHierarchy(unittest.TestCase):

    def test_add_component_happy_case(self):
        hierarchy = Hierarchy(name="NotRelevant", dimension_name="NotRelevant")
        hierarchy.add_element(element_name="c1", element_type="Consolidated")
        hierarchy.add_component(parent_name="c1", component_name="e1", weight=2)

        self.assertIn(("c1", "e1"), hierarchy.edges)
        self.assertEqual(hierarchy.edges[("c1", "e1")], 2)

    def test_add_component_component_existing(self):
        hierarchy = Hierarchy(name="NotRelevant", dimension_name="NotRelevant")
        hierarchy.add_element(element_name="c1", element_type="Consolidated")
        hierarchy.add_element(element_name="e1", element_type="Numeric")
        hierarchy.add_component(parent_name="c1", component_name="e1", weight=1)

        self.assertIn(("c1", "e1"), hierarchy.edges)
        self.assertEqual(hierarchy.edges[("c1", "e1")], 1)

    def test_add_component_parent_not_existing(self):
        hierarchy = Hierarchy(name="NotRelevant", dimension_name="NotRelevant")
        hierarchy.add_element(element_name="e1", element_type="Numeric")

        with self.assertRaises(ValueError) as error:
            hierarchy.add_component(parent_name="c1", component_name="e1", weight=1)
            print(str(error))

    def test_add_component_parent_is_string(self):
        hierarchy = Hierarchy(name="NotRelevant", dimension_name="NotRelevant")
        hierarchy.add_element(element_name="c1", element_type="String")
        hierarchy.add_element(element_name="e1", element_type="Numeric")

        with self.assertRaises(ValueError) as error:
            hierarchy.add_component(parent_name="c1", component_name="e1", weight=1)
            print(str(error))


if __name__ == '__main__':
    unittest.main()

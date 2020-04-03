import configparser
import unittest
from pathlib import Path

import pytest

from TM1py import Element
from TM1py.Exceptions import TM1pyException
from TM1py.Objects import Dimension, Hierarchy, Subset
from TM1py.Services import TM1Service

config = configparser.ConfigParser()
config.read(Path(__file__).parent.joinpath('config.ini'))

DIMENSION_PREFIX = 'TM1py_Tests_Hierarchy_'
DIMENSION_NAME = DIMENSION_PREFIX + "Some_Name"
SUBSET_NAME = DIMENSION_PREFIX + "Some_Subset"


class TestHierarchyMethods(unittest.TestCase):
    tm1 = None

    @classmethod
    def setup_class(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])

    @classmethod
    def teardown_class(cls):
        cls.tm1.logout()

    @classmethod
    def setUp(cls):
        cls.create_dimension()
        cls.create_subset()

    @classmethod
    def tearDown(cls):
        cls.delete_dimension()

    @classmethod
    def create_dimension(cls):
        dimension = Dimension(DIMENSION_NAME)
        hierarchy = Hierarchy(name=DIMENSION_NAME, dimension_name=DIMENSION_NAME)
        hierarchy.add_element('Total Years', 'Consolidated')
        hierarchy.add_element('No Year', 'Numeric')
        hierarchy.add_element('1989', 'Numeric')
        hierarchy.add_element("My Element", "Numeric")
        hierarchy.add_element_attribute('Previous Year', 'String')
        hierarchy.add_element_attribute('Next Year', 'String')
        hierarchy.add_edge('Total Years', '1989', 2)
        dimension.add_hierarchy(hierarchy)
        cls.tm1.dimensions.create(dimension)

    @classmethod
    def delete_dimension(cls):
        cls.tm1.dimensions.delete(DIMENSION_NAME)

    @classmethod
    def create_subset(cls):
        s = Subset(SUBSET_NAME, DIMENSION_NAME, DIMENSION_NAME,
                   expression="{{[{}].Members}}".format(DIMENSION_NAME))
        cls.tm1.dimensions.subsets.create(s, False)

    def add_other_hierarchy(self):
        dimension = self.tm1.dimensions.get(DIMENSION_NAME)
        # other hierarchy
        hierarchy = Hierarchy(name="Other Hierarchy", dimension_name=DIMENSION_NAME)
        hierarchy.add_element('Other Total Years', 'Consolidated')
        hierarchy.add_element('No Year', 'Numeric')
        hierarchy.add_element('1989', 'Numeric')
        hierarchy.add_element("Element With ' in the name", "Numeric")
        hierarchy.add_element_attribute('Previous Year', 'String')
        hierarchy.add_element_attribute('Next Year', 'String')
        hierarchy.add_edge('Other Total Years', '1989', 2)
        dimension.add_hierarchy(hierarchy)
        self.tm1.dimensions.update(dimension)

    def add_balanced_hierarchy(self, hierarchy_name):
        dimension = self.tm1.dimensions.get(DIMENSION_NAME)
        # other hierarchy
        hierarchy = Hierarchy(name=hierarchy_name, dimension_name=DIMENSION_NAME)

        hierarchy.add_element("Total Years Balanced", "Consolidated")
        hierarchy.add_element('1989', 'Numeric')
        hierarchy.add_element('1990', 'Numeric')
        hierarchy.add_element('1991', 'Numeric')
        hierarchy.add_edge("Total Years Balanced", "1989", 1)
        hierarchy.add_edge("Total Years Balanced", "1990", 1)
        hierarchy.add_edge("Total Years Balanced", "1991", 1)
        dimension.add_hierarchy(hierarchy)

        self.tm1.dimensions.update(dimension)

    def update_hierarchy(self):
        d = self.tm1.dimensions.get(dimension_name=DIMENSION_NAME)
        h = d.default_hierarchy
        # Edit Elements and Edges
        for year in range(2010, 2021, 1):
            parent = str(year)
            h.add_element(parent, 'Consolidated')
            h.add_edge('Total Years', parent, 1)
            for month in ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'):
                component = '{}-{}'.format(year, month)
                h.add_element(component, 'Numeric')
                h.add_edge(parent, component, 1)
        # Edit Element Attributes
        h.add_element_attribute('Name Long', 'Alias')
        h.add_element_attribute('Name Short', 'Alias')
        h.add_element_attribute('Days', 'Numeric')
        # Remove attribute
        h.remove_element_attribute('Next Year')
        # Remove Edge
        h.remove_edge('Total Years', '1989')
        # Update Edge
        h.update_edge('Total Years', '2011', 2)
        # Update_element
        h.update_element('No Year', 'String')
        self.tm1.dimensions.update(d)

    def test_get_hierarchy(self):
        h = self.tm1.dimensions.hierarchies.get(DIMENSION_NAME, DIMENSION_NAME)
        self.assertIn('Total Years', h.elements.keys())
        self.assertIn('No Year', h.elements.keys())
        self.assertIn('1989', h.elements.keys())
        self.assertIn('Next Year', [ea.name for ea in h.element_attributes])
        self.assertIn('Previous Year', [ea.name for ea in h.element_attributes])
        self.assertIn(SUBSET_NAME, h.subsets)

    def test_hierarchy___get__(self):
        h = self.tm1.dimensions.hierarchies.get(DIMENSION_NAME, DIMENSION_NAME)

        element = h["Total Years"]
        self.assertIsInstance(element, Element)
        self.assertEqual(element.name, "Total Years")
        self.assertEqual(element.element_type, Element.Types.CONSOLIDATED)
        element = h["Total Years".replace(" ", "").lower()]
        self.assertIsInstance(element, Element)
        self.assertEqual(element.name, "Total Years")
        self.assertEqual(element.element_type, Element.Types.CONSOLIDATED)

        element = h["1989"]
        self.assertIsInstance(element, Element)
        self.assertEqual(element.name, "1989")
        self.assertEqual(element.element_type, Element.Types.NUMERIC)
        self.assertNotEqual(element.element_type, Element.Types.STRING)

    def test_hierarchy___get__exception(self):
        h = self.tm1.dimensions.hierarchies.get(DIMENSION_NAME, DIMENSION_NAME)

        try:
            _ = h["Im not a valid year"]
            raise Exception("did not throw Exception when expected to do so")
        except ValueError:
            pass

    def test_hierarchy___contains__(self):
        h = self.tm1.dimensions.hierarchies.get(DIMENSION_NAME, DIMENSION_NAME)

        self.assertIn("1989", h)
        self.assertIn("Total Years", h)
        self.assertIn("Total Years".replace(" ", "").lower(), h)
        self.assertIn("1 9 8 9 ", h)
        self.assertNotIn("3001", h)

    def test_hierarchy___iter__(self):
        h = self.tm1.dimensions.hierarchies.get(DIMENSION_NAME, DIMENSION_NAME)
        elements_cloned_through_iter = [element for element in h]

        self.assertEqual(len(h._elements), len(elements_cloned_through_iter))
        for element in elements_cloned_through_iter:
            self.assertIn(element.name, h.elements)

    def test_hierarchy___len__(self):
        h = self.tm1.dimensions.hierarchies.get(DIMENSION_NAME, DIMENSION_NAME)
        self.assertGreater(len(h), 0)
        self.assertEqual(len(h), len(h._elements))

    def test_update_hierarchy(self):
        self.update_hierarchy()

        # Check if update works
        d = self.tm1.dimensions.get(DIMENSION_NAME)
        h = d.default_hierarchy
        self.assertIn('2010-Jan', h.elements.keys())
        self.assertIn('2020-Dec', h.elements.keys())

        self.assertNotIn('Next Year', [ea.name for ea in h.element_attributes])
        self.assertIn('Previous Year', [ea.name for ea in h.element_attributes])
        self.assertIn('Days', [ea.name for ea in h.element_attributes])
        self.assertIn('Name Long', [ea.name for ea in h.element_attributes])

        self.assertEqual(h.edges[('Total Years', '2011')], 2)
        self.assertEqual(h.elements['No Year'].element_type, Element.Types.STRING)

        summary = self.tm1.dimensions.hierarchies.get_hierarchy_summary(DIMENSION_NAME, DIMENSION_NAME)
        self.assertEqual(summary["Elements"], 147)
        self.assertEqual(summary["Edges"], 143)
        self.assertEqual(summary["Members"], 147)
        self.assertEqual(summary["ElementAttributes"], 4)
        self.assertEqual(summary["Levels"], 3)

    def test_update_hierarchy_remove_c_element(self):
        self.update_hierarchy()

        d = self.tm1.dimensions.get(DIMENSION_NAME)
        h = d.default_hierarchy
        self.assertIn('2011', h.elements)
        self.assertIn(('2011', '2011-Jan'), h.edges)

        h.remove_element('2011')
        self.tm1.dimensions.hierarchies.update(h)

        d = self.tm1.dimensions.get(DIMENSION_NAME)
        h = d.default_hierarchy
        self.assertNotIn('2011', h.elements)
        self.assertNotIn(('2011', '2011-Jan'), h.edges)

    def test_update_hierarchy_remove_n_element(self):
        self.update_hierarchy()

        d = self.tm1.dimensions.get(DIMENSION_NAME)
        h = d.default_hierarchy
        self.assertIn('2011-Jan', h.elements)
        self.assertIn(('2011', '2011-Jan'), h.edges)

        h.remove_element('2011-Jan')
        self.tm1.dimensions.hierarchies.update(h)

        d = self.tm1.dimensions.get(DIMENSION_NAME)
        h = d.default_hierarchy
        self.assertNotIn('2011-Jan', h.elements)
        self.assertNotIn(('2011', '2011-Jan'), h.edges)

    def test_update_hierarchy_remove_s_element(self):
        self.update_hierarchy()

        d = self.tm1.dimensions.get(DIMENSION_NAME)
        h = d.default_hierarchy
        self.assertIn('No Year', h.elements)

        h.remove_element('No Year')
        self.tm1.dimensions.hierarchies.update(h)

        d = self.tm1.dimensions.get(DIMENSION_NAME)
        h = d.default_hierarchy
        self.assertNotIn('No Year', h.elements)

    def test_update_hierarchy_remove_edges_related_to_element(self):
        self.update_hierarchy()

        d = self.tm1.dimensions.get(DIMENSION_NAME)
        h = d.default_hierarchy
        self.assertIn('2012', h.elements)

        h.remove_edges_related_to_element(element_name='2012 ')
        self.tm1.dimensions.hierarchies.update(h)

        d = self.tm1.dimensions.get(DIMENSION_NAME)
        h = d.default_hierarchy
        self.assertIn('2012', h.elements)
        self.assertNotIn(('2012', '2012- Jan'), h.edges)
        self.assertNotIn(('2012', '2012-DEC'), h.edges)
        self.assertNotIn(('TotalYears', '2012'), h.edges)
        self.assertIn(('Total YEARS', '2011'), h.edges)
        self.assertIn(('Total Years', '2013'), h.edges)

    def test_update_hierarchy_remove_edges(self):
        self.update_hierarchy()

        d = self.tm1.dimensions.get(DIMENSION_NAME)
        h = d.default_hierarchy
        self.assertIn('2012', h.elements)
        self.assertIn(('2012', '2012-Jan'), h.edges)
        self.assertIn(('2012', '2012-Feb'), h.edges)
        self.assertIn(('2012', '2012-Mar'), h.edges)
        self.assertIn(('2012', '2012-Apr'), h.edges)

        edges = [('2012', '2012- Jan'), ('2012', '2012-Feb'), ('2012', '2012-MAR'), ('2012', '2012-Apr')]
        h.remove_edges(edges=edges)
        self.tm1.dimensions.hierarchies.update(h)

        d = self.tm1.dimensions.get(DIMENSION_NAME)
        h = d.default_hierarchy

        self.assertNotIn(('2012', '2012-Jan'), h.edges)
        self.assertNotIn(('2012', '2012-Feb'), h.edges)
        self.assertNotIn(('2012', '2012-Mar'), h.edges)
        self.assertNotIn(('2012', '2012-Apr'), h.edges)
        self.assertNotIn(('2012', '2012 - JAN'), h.edges)
        self.assertIn(('2012', '2012-May'), h.edges)

        self.assertIn('2012', h.elements)
        self.assertIn('2012-Feb', h.elements)

    def test_hierarchy_summary(self):
        summary = self.tm1.dimensions.hierarchies.get_hierarchy_summary(DIMENSION_NAME, DIMENSION_NAME)
        self.assertEqual(summary["Elements"], 4)
        self.assertEqual(summary["Edges"], 1)
        self.assertEqual(summary["Members"], 4)
        self.assertEqual(summary["ElementAttributes"], 2)
        self.assertEqual(summary["Levels"], 2)

    def test_get_default_member(self):
        default_member = self.tm1.dimensions.hierarchies.get_default_member(DIMENSION_NAME, DIMENSION_NAME)
        self.assertEqual(default_member, "Total Years")

    def test_get_default_member_for_leaves_hierarchy(self):
        self.add_other_hierarchy()
        default_member = self.tm1.dimensions.hierarchies.get_default_member(
            dimension_name=DIMENSION_NAME,
            hierarchy_name="Leaves")
        self.assertEqual(default_member, "No Year")

    def test_update_default_member(self):
        default_member = self.tm1.dimensions.hierarchies.get_default_member(DIMENSION_NAME, DIMENSION_NAME)
        self.assertEqual(default_member, "Total Years")
        self.tm1.dimensions.hierarchies.update_default_member(DIMENSION_NAME, DIMENSION_NAME, member_name="1989")
        default_member = self.tm1.dimensions.hierarchies.get_default_member(DIMENSION_NAME, DIMENSION_NAME)
        self.assertEqual(default_member, "1989")

    def test_update_default_member_skip_hierarchy_name_argument(self):
        default_member = self.tm1.dimensions.hierarchies.get_default_member(DIMENSION_NAME)
        self.assertEqual(default_member, "Total Years")
        self.tm1.dimensions.hierarchies.update_default_member(dimension_name=DIMENSION_NAME, member_name="1989")
        default_member = self.tm1.dimensions.hierarchies.get_default_member(DIMENSION_NAME)
        self.assertEqual(default_member, "1989")

    def test_update_default_member_for_alternate_hierarchy(self):
        self.add_other_hierarchy()
        default_member = self.tm1.dimensions.hierarchies.get_default_member(DIMENSION_NAME, "Other Hierarchy")
        self.assertEqual(default_member, "Other Total Years")
        self.tm1.dimensions.hierarchies.update_default_member(DIMENSION_NAME, DIMENSION_NAME, member_name="1989")
        default_member = self.tm1.dimensions.hierarchies.get_default_member(DIMENSION_NAME, DIMENSION_NAME)
        self.assertEqual(default_member, "1989")

    def test_update_default_member_for_leaves_hierarchy(self):
        self.add_other_hierarchy()
        default_member = self.tm1.dimensions.hierarchies.get_default_member(DIMENSION_NAME, "Leaves")
        self.assertEqual(default_member, "No Year")
        self.tm1.dimensions.hierarchies.update_default_member(DIMENSION_NAME, DIMENSION_NAME, member_name="1989")
        default_member = self.tm1.dimensions.hierarchies.get_default_member(DIMENSION_NAME, DIMENSION_NAME)
        self.assertEqual(default_member, "1989")

    def test_update_default_member_with_invalid_value(self):
        default_member = self.tm1.dimensions.hierarchies.get_default_member(DIMENSION_NAME, DIMENSION_NAME)
        self.assertEqual(default_member, "Total Years")
        self.tm1.dimensions.hierarchies.update_default_member(
            DIMENSION_NAME,
            DIMENSION_NAME,
            member_name="I am not a valid Member")
        default_member = self.tm1.dimensions.hierarchies.get_default_member(DIMENSION_NAME, DIMENSION_NAME)
        self.assertEqual(default_member, "Total Years")

    def test_remove_all_edges(self):
        hierarchy = self.tm1.dimensions.hierarchies.get(DIMENSION_NAME, DIMENSION_NAME)
        self.assertGreater(len(hierarchy.edges), 0)
        self.tm1.dimensions.hierarchies.remove_all_edges(DIMENSION_NAME, DIMENSION_NAME)
        hierarchy = self.tm1.dimensions.hierarchies.get(DIMENSION_NAME, DIMENSION_NAME)
        self.assertEqual(len(hierarchy.edges), 0)

    def test_add_edges(self):
        edges = {("Total Years", "My Element"): 1, ("Total Years", "No Year"): 1}
        self.tm1.dimensions.hierarchies.add_edges(DIMENSION_NAME, DIMENSION_NAME, edges)

        hierarchy = self.tm1.dimensions.hierarchies.get(DIMENSION_NAME, DIMENSION_NAME)
        self.assertEqual(hierarchy.edges[("Total Years", "My Element")], 1)
        self.assertEqual(hierarchy.edges[("Total Years", "No Year")], 1)

    def test_add_edges_fail_existing(self):
        edges = {("Total Years", "1989"): 1}
        with pytest.raises(TM1pyException):
            self.tm1.dimensions.hierarchies.add_edges(DIMENSION_NAME, DIMENSION_NAME, edges)

    def test_is_balanced_false(self):
        is_balanced = self.tm1.dimensions.hierarchies.is_balanced(DIMENSION_NAME, DIMENSION_NAME)
        self.assertFalse(is_balanced)

    def test_is_balanced_true(self):
        balanced_hierarchy_name = "Balanced Hierarchy"
        self.add_balanced_hierarchy(balanced_hierarchy_name)

        is_balanced = self.tm1.dimensions.hierarchies.is_balanced(DIMENSION_NAME, balanced_hierarchy_name)
        self.assertTrue(is_balanced)


if __name__ == '__main__':
    unittest.main()

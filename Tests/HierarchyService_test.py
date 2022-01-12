import configparser
import unittest
from pathlib import Path

from TM1py import Element, ElementAttribute
from TM1py.Exceptions import TM1pyException
from TM1py.Objects import Dimension, Hierarchy, Subset
from TM1py.Services import TM1Service


class TestHierarchyService(unittest.TestCase):
    tm1: TM1Service
    prefix = 'TM1py_Tests_Hierarchy_'
    dimension_name = prefix + "Some_Name"
    subset_name = prefix + "Some_Subset"

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM! objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])

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
        dimension = Dimension(cls.dimension_name)
        hierarchy = Hierarchy(name=cls.dimension_name, dimension_name=cls.dimension_name)
        hierarchy.add_element('Total Years', 'Consolidated')
        hierarchy.add_element('No Year', 'Numeric')
        hierarchy.add_element('1989', 'Numeric')
        hierarchy.add_element("My Element", "Numeric")
        hierarchy.add_element_attribute('Previous Year', 'String')
        hierarchy.add_element_attribute('Next Year', 'String')
        hierarchy.add_element_attribute('Updateable Attribute', 'String')
        hierarchy.add_edge('Total Years', '1989', 2)
        dimension.add_hierarchy(hierarchy)
        cls.tm1.dimensions.create(dimension)

    @classmethod
    def delete_dimension(cls):
        cls.tm1.dimensions.delete(cls.dimension_name)

    @classmethod
    def create_subset(cls):
        s = Subset(cls.subset_name, cls.dimension_name, cls.dimension_name,
                   expression="{{[{}].Members}}".format(cls.dimension_name))
        cls.tm1.dimensions.subsets.create(s, False)

    def add_other_hierarchy(self):
        dimension = self.tm1.dimensions.get(self.dimension_name)
        # other hierarchy
        hierarchy = Hierarchy(name="Other Hierarchy", dimension_name=self.dimension_name)
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
        dimension = self.tm1.dimensions.get(self.dimension_name)
        # other hierarchy
        hierarchy = Hierarchy(name=hierarchy_name, dimension_name=self.dimension_name)

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
        d = self.tm1.dimensions.get(dimension_name=self.dimension_name)
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
        # Change attribute type
        h.remove_element_attribute('Updateable Attribute')
        h.add_element_attribute("Updateable Attribute", "Numeric")
        # Remove Edge
        h.remove_edge('Total Years', '1989')
        # Update Edge
        h.update_edge('Total Years', '2011', 2)
        # Update_element
        h.update_element('No Year', 'String')
        self.tm1.dimensions.update(d)

    def test_get_hierarchy(self):
        h = self.tm1.dimensions.hierarchies.get(self.dimension_name, self.dimension_name)
        self.assertIn('Total Years', h.elements.keys())
        self.assertIn('No Year', h.elements.keys())
        self.assertIn('1989', h.elements.keys())
        self.assertIn('Next Year', [ea.name for ea in h.element_attributes])
        self.assertIn('Previous Year', [ea.name for ea in h.element_attributes])
        self.assertIn(self.subset_name, h.subsets)

    def test_hierarchy___get__(self):
        h = self.tm1.dimensions.hierarchies.get(self.dimension_name, self.dimension_name)

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
        h = self.tm1.dimensions.hierarchies.get(self.dimension_name, self.dimension_name)

        try:
            _ = h["Im not a valid year"]
            raise Exception("did not throw Exception when expected to do so")
        except ValueError:
            pass

    def test_hierarchy___contains__(self):
        h = self.tm1.dimensions.hierarchies.get(self.dimension_name, self.dimension_name)

        self.assertIn("1989", h)
        self.assertIn("Total Years", h)
        self.assertIn("Total Years".replace(" ", "").lower(), h)
        self.assertIn("1 9 8 9 ", h)
        self.assertNotIn("3001", h)

    def test_hierarchy___iter__(self):
        h = self.tm1.dimensions.hierarchies.get(self.dimension_name, self.dimension_name)
        elements_cloned_through_iter = [element for element in h]

        self.assertEqual(len(h._elements), len(elements_cloned_through_iter))
        for element in elements_cloned_through_iter:
            self.assertIn(element.name, h.elements)

    def test_hierarchy___len__(self):
        h = self.tm1.dimensions.hierarchies.get(self.dimension_name, self.dimension_name)
        self.assertGreater(len(h), 0)
        self.assertEqual(len(h), len(h._elements))

    def test_update_hierarchy(self):
        self.update_hierarchy()

        # Check if update works
        d = self.tm1.dimensions.get(self.dimension_name)
        h = d.default_hierarchy
        self.assertIn('2010-Jan', h.elements.keys())
        self.assertIn('2020-Dec', h.elements.keys())

        self.assertNotIn(ElementAttribute('Next Year', 'String'), h.element_attributes)
        self.assertIn(ElementAttribute('Previous Year', 'String'), h.element_attributes)
        self.assertIn(ElementAttribute('Days', 'String'), h.element_attributes)
        self.assertIn(ElementAttribute('Name Long', 'String'), h.element_attributes)
        self.assertIn(ElementAttribute('Updateable Attribute', 'Numeric'), h.element_attributes)

        self.assertEqual(h.edges[('Total Years', '2011')], 2)
        self.assertEqual(h.elements['No Year'].element_type, Element.Types.STRING)

        summary = self.tm1.dimensions.hierarchies.get_hierarchy_summary(self.dimension_name, self.dimension_name)
        self.assertEqual(summary["Elements"], 147)
        self.assertEqual(summary["Edges"], 143)
        self.assertEqual(summary["Members"], 147)
        self.assertEqual(summary["ElementAttributes"], 5)
        self.assertEqual(summary["Levels"], 3)

    def test_update_hierarchy_remove_c_element(self):
        self.update_hierarchy()

        d = self.tm1.dimensions.get(self.dimension_name)
        h = d.default_hierarchy
        self.assertIn('2011', h.elements)
        self.assertIn(('2011', '2011-Jan'), h.edges)

        h.remove_element('2011')
        self.tm1.dimensions.hierarchies.update(h)

        d = self.tm1.dimensions.get(self.dimension_name)
        h = d.default_hierarchy
        self.assertNotIn('2011', h.elements)
        self.assertNotIn(('2011', '2011-Jan'), h.edges)

    def test_update_hierarchy_remove_n_element(self):
        self.update_hierarchy()

        d = self.tm1.dimensions.get(self.dimension_name)
        h = d.default_hierarchy
        self.assertIn('2011-Jan', h.elements)
        self.assertIn(('2011', '2011-Jan'), h.edges)

        h.remove_element('2011-Jan')
        self.tm1.dimensions.hierarchies.update(h)

        d = self.tm1.dimensions.get(self.dimension_name)
        h = d.default_hierarchy
        self.assertNotIn('2011-Jan', h.elements)
        self.assertNotIn(('2011', '2011-Jan'), h.edges)

    def test_update_hierarchy_remove_s_element(self):
        self.update_hierarchy()

        d = self.tm1.dimensions.get(self.dimension_name)
        h = d.default_hierarchy
        self.assertIn('No Year', h.elements)

        h.remove_element('No Year')
        self.tm1.dimensions.hierarchies.update(h)

        d = self.tm1.dimensions.get(self.dimension_name)
        h = d.default_hierarchy
        self.assertNotIn('No Year', h.elements)

    def test_update_hierarchy_remove_edges_related_to_element(self):
        self.update_hierarchy()

        d = self.tm1.dimensions.get(self.dimension_name)
        h = d.default_hierarchy
        self.assertIn('2012', h.elements)

        h.remove_edges_related_to_element(element_name='2012 ')
        self.tm1.dimensions.hierarchies.update(h)

        d = self.tm1.dimensions.get(self.dimension_name)
        h = d.default_hierarchy
        self.assertIn('2012', h.elements)
        self.assertNotIn(('2012', '2012- Jan'), h.edges)
        self.assertNotIn(('2012', '2012-DEC'), h.edges)
        self.assertNotIn(('TotalYears', '2012'), h.edges)
        self.assertIn(('Total YEARS', '2011'), h.edges)
        self.assertIn(('Total Years', '2013'), h.edges)

    def test_update_hierarchy_remove_edges(self):
        self.update_hierarchy()

        d = self.tm1.dimensions.get(self.dimension_name)
        h = d.default_hierarchy
        self.assertIn('2012', h.elements)
        self.assertIn(('2012', '2012-Jan'), h.edges)
        self.assertIn(('2012', '2012-Feb'), h.edges)
        self.assertIn(('2012', '2012-Mar'), h.edges)
        self.assertIn(('2012', '2012-Apr'), h.edges)

        edges = [('2012', '2012- Jan'), ('2012', '2012-Feb'), ('2012', '2012-MAR'), ('2012', '2012-Apr')]
        h.remove_edges(edges=edges)
        self.tm1.dimensions.hierarchies.update(h)

        d = self.tm1.dimensions.get(self.dimension_name)
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
        summary = self.tm1.dimensions.hierarchies.get_hierarchy_summary(self.dimension_name, self.dimension_name)
        self.assertEqual(summary["Elements"], 4)
        self.assertEqual(summary["Edges"], 1)
        self.assertEqual(summary["Members"], 4)
        self.assertEqual(summary["ElementAttributes"], 3)
        self.assertEqual(summary["Levels"], 2)

    def test_get_default_member(self):
        default_member = self.tm1.dimensions.hierarchies.get_default_member(self.dimension_name, self.dimension_name)
        self.assertEqual(default_member, "Total Years")

    def test_get_default_member_for_leaves_hierarchy(self):
        self.add_other_hierarchy()
        default_member = self.tm1.dimensions.hierarchies.get_default_member(
            dimension_name=self.dimension_name,
            hierarchy_name="Leaves")
        self.assertEqual(default_member, "No Year")

    def test_update_default_member(self):
        default_member = self.tm1.dimensions.hierarchies.get_default_member(self.dimension_name, self.dimension_name)
        self.assertEqual(default_member, "Total Years")
        self.tm1.dimensions.hierarchies.update_default_member(self.dimension_name, self.dimension_name, "1989")
        default_member = self.tm1.dimensions.hierarchies.get_default_member(self.dimension_name, self.dimension_name)
        self.assertEqual(default_member, "1989")

    def test_update_default_member_skip_hierarchy_name_argument(self):
        default_member = self.tm1.dimensions.hierarchies.get_default_member(self.dimension_name)
        self.assertEqual(default_member, "Total Years")
        self.tm1.dimensions.hierarchies.update_default_member(dimension_name=self.dimension_name, member_name="1989")
        default_member = self.tm1.dimensions.hierarchies.get_default_member(self.dimension_name)
        self.assertEqual(default_member, "1989")

    def test_update_default_member_for_alternate_hierarchy(self):
        self.add_other_hierarchy()
        default_member = self.tm1.dimensions.hierarchies.get_default_member(self.dimension_name, "Other Hierarchy")
        self.assertEqual(default_member, "Other Total Years")
        self.tm1.dimensions.hierarchies.update_default_member(self.dimension_name, self.dimension_name, "1989")
        default_member = self.tm1.dimensions.hierarchies.get_default_member(self.dimension_name, self.dimension_name)
        self.assertEqual(default_member, "1989")

    def test_update_default_member_for_leaves_hierarchy(self):
        self.add_other_hierarchy()
        default_member = self.tm1.dimensions.hierarchies.get_default_member(self.dimension_name, "Leaves")
        self.assertEqual(default_member, "No Year")
        self.tm1.dimensions.hierarchies.update_default_member(self.dimension_name, self.dimension_name, "1989")
        default_member = self.tm1.dimensions.hierarchies.get_default_member(self.dimension_name, self.dimension_name)
        self.assertEqual(default_member, "1989")

    def test_update_default_member_with_invalid_value(self):
        default_member = self.tm1.dimensions.hierarchies.get_default_member(self.dimension_name, self.dimension_name)
        self.assertEqual(default_member, "Total Years")
        self.tm1.dimensions.hierarchies.update_default_member(
            self.dimension_name,
            self.dimension_name,
            member_name="I am not a valid Member")
        default_member = self.tm1.dimensions.hierarchies.get_default_member(self.dimension_name, self.dimension_name)
        self.assertEqual(default_member, "Total Years")

    def test_remove_all_edges(self):
        hierarchy = self.tm1.dimensions.hierarchies.get(self.dimension_name, self.dimension_name)
        self.assertGreater(len(hierarchy.edges), 0)
        self.tm1.dimensions.hierarchies.remove_all_edges(self.dimension_name, self.dimension_name)
        hierarchy = self.tm1.dimensions.hierarchies.get(self.dimension_name, self.dimension_name)
        self.assertEqual(len(hierarchy.edges), 0)

    def test_remove_edges_under_consolidation(self):
        members = self.tm1.dimensions.hierarchies.elements.get_members_under_consolidation(
            self.dimension_name,
            self.dimension_name,
            'Total Years')
        self.assertGreater(len(members), 0)
        self.tm1.dimensions.hierarchies.remove_edges_under_consolidation(
            self.dimension_name,
            self.dimension_name,
            'Total Years')
        members = self.tm1.dimensions.hierarchies.elements.get_members_under_consolidation(
            self.dimension_name,
            self.dimension_name,
            'Total Years')
        self.assertEqual(len(members), 0)

    def test_add_edges(self):
        edges = {("Total Years", "My Element"): 1, ("Total Years", "No Year"): 1}
        self.tm1.dimensions.hierarchies.add_edges(self.dimension_name, self.dimension_name, edges)

        hierarchy = self.tm1.dimensions.hierarchies.get(self.dimension_name, self.dimension_name)
        self.assertEqual(hierarchy.edges[("Total Years", "My Element")], 1)
        self.assertEqual(hierarchy.edges[("Total Years", "No Year")], 1)

    def test_add_edges_fail_existing(self):
        with self.assertRaises(TM1pyException) as _:
            edges = {("Total Years", "1989"): 1}
            self.tm1.dimensions.hierarchies.add_edges(self.dimension_name, self.dimension_name, edges)

    def test_is_balanced_false(self):
        is_balanced = self.tm1.dimensions.hierarchies.is_balanced(self.dimension_name, self.dimension_name)
        self.assertFalse(is_balanced)

    def test_is_balanced_true(self):
        balanced_hierarchy_name = "Balanced Hierarchy"
        self.add_balanced_hierarchy(balanced_hierarchy_name)

        is_balanced = self.tm1.dimensions.hierarchies.is_balanced(self.dimension_name, balanced_hierarchy_name)
        self.assertTrue(is_balanced)

    def test_hierarchy_remove_all_elements(self):
        hierarchy = self.tm1.hierarchies.get(self.dimension_name, self.dimension_name)
        self.assertGreater(len(hierarchy.elements), 0)
        self.assertGreater(len(hierarchy.edges), 0)

        hierarchy.remove_all_elements()
        self.tm1.hierarchies.update(hierarchy)

        hierarchy = self.tm1.hierarchies.get(self.dimension_name, self.dimension_name)
        self.assertEqual(len(hierarchy.elements), 0)
        self.assertEqual(len(hierarchy.edges), 0)

    def test_hierarchy_remove_all_edges(self):
        hierarchy = self.tm1.hierarchies.get(self.dimension_name, self.dimension_name)
        self.assertGreater(len(hierarchy.elements), 0)
        self.assertGreater(len(hierarchy.edges), 0)

        hierarchy.remove_all_edges()
        self.tm1.hierarchies.update(hierarchy)

        hierarchy = self.tm1.hierarchies.get(self.dimension_name, self.dimension_name)
        self.assertGreater(len(hierarchy.elements), 0)
        self.assertEqual(len(hierarchy.edges), 0)


if __name__ == '__main__':
    unittest.main()

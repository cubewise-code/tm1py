import unittest

from TM1py import Hierarchy, Element


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

    def test_get_ancestors(self):
        hierarchy = Hierarchy(
            name="NotRelevant",
            dimension_name="NotRelevant",
            elements=[
                Element("Total", "Consolidated"),
                Element("Europe", "Consolidated"),
                Element("DACH", "Consolidated"),
                Element("Germany", "Numeric"),
                Element("Switzerland", "Numeric"),
                Element("Austria", "Numeric"),
                Element("France", "Numeric"),
                Element("Other", "Numeric"),
            ],
            edges={
                ("Total", "Europe"): 1,
                ("Europe", "DACH"): 1,
                ("DACH", "Germany"): 1,
                ("DACH", "Switzerland"): 1,
                ("DACH", "Austria"): 1,
                ("Europe", "France"): 1,
            },
        )

        elements = hierarchy.get_ancestors("Germany", recursive=False)
        self.assertEqual({Element("DACH", "Consolidated")}, elements)

    def test_get_ancestors_recursive(self):
        hierarchy = Hierarchy(
            name="NotRelevant",
            dimension_name="NotRelevant",
            elements=[
                Element("Total", "Consolidated"),
                Element("Europe", "Consolidated"),
                Element("DACH", "Consolidated"),
                Element("Germany", "Numeric"),
                Element("Switzerland", "Numeric"),
                Element("Austria", "Numeric"),
                Element("France", "Numeric"),
                Element("Other", "Numeric"),
            ],
            edges={
                ("Total", "Europe"): 1,
                ("Europe", "DACH"): 1,
                ("DACH", "Germany"): 1,
                ("DACH", "Switzerland"): 1,
                ("DACH", "Austria"): 1,
                ("Europe", "France"): 1,
            },
        )

        elements = hierarchy.get_ancestors("Germany", recursive=True)
        self.assertEqual(
            {Element("DACH", "Consolidated"), Element("Europe", "Consolidated"), Element("Total", "Consolidated")},
            elements,
        )

    def test_get_descendants(self):
        hierarchy = Hierarchy(
            name="NotRelevant",
            dimension_name="NotRelevant",
            elements=[
                Element("Total", "Consolidated"),
                Element("Europe", "Consolidated"),
                Element("DACH", "Consolidated"),
                Element("Germany", "Numeric"),
                Element("Switzerland", "Numeric"),
                Element("Austria", "Numeric"),
                Element("France", "Numeric"),
                Element("Other", "Numeric"),
            ],
            edges={
                ("Total", "Europe"): 1,
                ("Europe", "DACH"): 1,
                ("DACH", "Germany"): 1,
                ("DACH", "Switzerland"): 1,
                ("DACH", "Austria"): 1,
                ("Europe", "France"): 1,
            },
        )

        elements = hierarchy.get_descendants("DACH")
        self.assertEqual(
            {Element("Germany", "Numeric"), Element("Austria", "Numeric"), Element("Switzerland", "Numeric")}, elements
        )

    def test_get_descendants_recursive(self):
        hierarchy = Hierarchy(
            name="NotRelevant",
            dimension_name="NotRelevant",
            elements=[
                Element("Total", "Consolidated"),
                Element("Europe", "Consolidated"),
                Element("DACH", "Consolidated"),
                Element("Germany", "Numeric"),
                Element("Switzerland", "Numeric"),
                Element("Austria", "Numeric"),
                Element("France", "Numeric"),
                Element("Other", "Numeric"),
            ],
            edges={
                ("Total", "Europe"): 1,
                ("Europe", "DACH"): 1,
                ("DACH", "Germany"): 1,
                ("DACH", "Switzerland"): 1,
                ("DACH", "Austria"): 1,
                ("Europe", "France"): 1,
            },
        )

        elements = hierarchy.get_descendants("Europe", recursive=True)
        self.assertEqual(
            {
                Element("DACH", "Consolidated"),
                Element("Germany", "Numeric"),
                Element("Austria", "Numeric"),
                Element("Switzerland", "Numeric"),
                Element("France", "Numeric"),
            },
            elements,
        )

    def test_get_descendants_recursive_leaves_only(self):
        hierarchy = Hierarchy(
            name="NotRelevant",
            dimension_name="NotRelevant",
            elements=[
                Element("Total", "Consolidated"),
                Element("Europe", "Consolidated"),
                Element("DACH", "Consolidated"),
                Element("Germany", "Numeric"),
                Element("Switzerland", "Numeric"),
                Element("Austria", "Numeric"),
                Element("France", "Numeric"),
                Element("Other", "Numeric"),
            ],
            edges={
                ("Total", "Europe"): 1,
                ("Europe", "DACH"): 1,
                ("DACH", "Germany"): 1,
                ("DACH", "Switzerland"): 1,
                ("DACH", "Austria"): 1,
                ("Europe", "France"): 1,
            },
        )

        elements = hierarchy.get_descendants("Europe", recursive=True, leaves_only=True)
        self.assertEqual(
            {Element("Germany", "Numeric"), Element("Austria", "Numeric"),
             Element("Switzerland", "Numeric"), Element("France", "Numeric")},
            elements)
        
    def test_get_descendants_recursive_leaves_only_with_higher_level_consolidation(self):
        hierarchy = Hierarchy(
            name="NotRelevant",
            dimension_name="NotRelevant",
            elements=[
                Element("Total", "Consolidated"),
                Element("A", "Consolidated"),
                Element("B", "Consolidated"),
                Element("C", "Consolidated"),
                Element("AA", "Consolidated"),
                Element("BBC", "Numeric"),
                Element("CCC", "Numeric"),
                Element("AAA", "Numeric"),
                Element("AAB", "Numeric"),
                Element("AAC", "Numeric")],
            edges={
                ("Total", "A"): 1,
                ("A", "AA"): 1,
                ("AA", "AAA"): 1,
                ("AA", "AAB"): 1,
                ("AA", "AAC"): 1,
                ("Total", "B"): 1,
                ("B", "BBC"): 1,
                ("Total", "C"): 1,
                ("C", "CCC"): 1,
            })

        elements = hierarchy.get_descendants("Total", recursive=True, leaves_only=True)
        self.assertEqual(
            {Element("BBC", "Numeric"), Element("CCC", "Numeric"), Element("AAA", "Numeric"), Element("AAB", "Numeric"), Element("AAC", "Numeric")},
            elements)

    def test_get_descendant_edges_recursive_false(self):
        hierarchy = Hierarchy(
            name="NotRelevant",
            dimension_name="NotRelevant",
            elements=[
                Element("Total", "Consolidated"),
                Element("Europe", "Consolidated"),
                Element("DACH", "Consolidated"),
                Element("Germany", "Numeric"),
                Element("Switzerland", "Numeric"),
                Element("Austria", "Numeric"),
                Element("France", "Numeric"),
                Element("Other", "Numeric"),
            ],
            edges={
                ("Total", "Europe"): 1,
                ("Europe", "DACH"): 1,
                ("DACH", "Germany"): 1,
                ("DACH", "Switzerland"): 1,
                ("DACH", "Austria"): 1,
                ("Europe", "France"): 1,
            },
        )

        edges = hierarchy.get_descendant_edges("Europe")
        self.assertEqual({("Europe", "DACH"): 1, ("Europe", "France"): 1}, edges)

    def test_get_descendant_edges_recursive_true(self):
        hierarchy = Hierarchy(
            name="NotRelevant",
            dimension_name="NotRelevant",
            elements=[
                Element("Total", "Consolidated"),
                Element("Europe", "Consolidated"),
                Element("DACH", "Consolidated"),
                Element("Germany", "Numeric"),
                Element("Switzerland", "Numeric"),
                Element("Austria", "Numeric"),
                Element("France", "Numeric"),
                Element("Other", "Numeric"),
            ],
            edges={
                ("Total", "Europe"): 1,
                ("Europe", "DACH"): 1,
                ("DACH", "Germany"): 1,
                ("DACH", "Switzerland"): 1,
                ("DACH", "Austria"): 1,
                ("Europe", "France"): 1,
            },
        )

        edges = hierarchy.get_descendant_edges("Europe", recursive=True)
        self.assertEqual(
            {
                ("Europe", "DACH"): 1,
                ("DACH", "Germany"): 1,
                ("DACH", "Switzerland"): 1,
                ("DACH", "Austria"): 1,
                ("Europe", "France"): 1,
            },
            edges,
        )

    def test_replace_element_consolidation(self):
        hierarchy = Hierarchy(
            name="NotRelevant",
            dimension_name="NotRelevant",
            elements=[
                Element("Total", "Consolidated"),
                Element("Europe", "Consolidated"),
                Element("DACH", "Consolidated"),
                Element("Germany", "Numeric"),
                Element("Switzerland", "Numeric"),
                Element("Austria", "Numeric"),
                Element("France", "Numeric"),
                Element("Other", "Numeric"),
            ],
            edges={
                ("Total", "Europe"): 1,
                ("Europe", "DACH"): 1,
                ("DACH", "Germany"): 1,
                ("DACH", "Switzerland"): 1,
                ("DACH", "Austria"): 1,
                ("Europe", "France"): 1,
            },
        )

        hierarchy.replace_element(old_element_name="Europe", new_element_name="Europa")

        self.assertIn("Europa", hierarchy)
        self.assertNotIn("Europe", hierarchy)

        self.assertIn(("Total", "Europa"), hierarchy.edges)
        self.assertNotIn(("Total", "Europe"), hierarchy.edges)
        self.assertIn(("Europa", "DACH"), hierarchy.edges)
        self.assertNotIn(("Europe", "DACH"), hierarchy.edges)
        self.assertIn(("Europa", "France"), hierarchy.edges)
        self.assertNotIn(("Europe", "France"), hierarchy.edges)

    def test_replace_element_leaf(self):
        hierarchy = Hierarchy(
            name="NotRelevant",
            dimension_name="NotRelevant",
            elements=[
                Element("Total", "Consolidated"),
                Element("Europe", "Consolidated"),
                Element("DACH", "Consolidated"),
                Element("Germany", "Numeric"),
                Element("Switzerland", "Numeric"),
                Element("Austria", "Numeric"),
                Element("France", "Numeric"),
                Element("Other", "Numeric"),
            ],
            edges={
                ("Total", "Europe"): 1,
                ("Europe", "DACH"): 1,
                ("DACH", "Germany"): 1,
                ("DACH", "Switzerland"): 1,
                ("DACH", "Austria"): 1,
                ("Europe", "France"): 1,
            },
        )

        hierarchy.replace_element(old_element_name="Switzerland", new_element_name="Schweiz")

        self.assertIn("Schweiz", hierarchy)
        self.assertNotIn("Switzerland", hierarchy)

        self.assertIn(("DACH", "Schweiz"), hierarchy.edges)
        self.assertNotIn(("DACH", "Switzerland"), hierarchy.edges)


if __name__ == "__main__":
    unittest.main()

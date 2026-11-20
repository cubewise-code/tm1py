import unittest
import warnings

from TM1py import Element, Hierarchy


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
            {
                Element("Germany", "Numeric"),
                Element("Austria", "Numeric"),
                Element("Switzerland", "Numeric"),
                Element("France", "Numeric"),
            },
            elements,
        )

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
                Element("AAC", "Numeric"),
            ],
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
            },
        )

        elements = hierarchy.get_descendants("Total", recursive=True, leaves_only=True)
        self.assertEqual(
            {
                Element("BBC", "Numeric"),
                Element("CCC", "Numeric"),
                Element("AAA", "Numeric"),
                Element("AAB", "Numeric"),
                Element("AAC", "Numeric"),
            },
            elements,
        )

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

    @staticmethod
    def build_hierarchy(edges: dict, numeric: list = (), strings: list = ()) -> Hierarchy:
        """consolidations are derived from the edges; standalone leaves can be added with numeric / strings"""
        parents = {parent for parent, _ in edges}
        components = {component for _, component in edges}
        elements = [Element(name, "Consolidated") for name in sorted(parents)]
        elements += [Element(name, "Numeric") for name in sorted((components - parents) | set(numeric))]
        elements += [Element(name, "String") for name in strings]
        return Hierarchy(name="Product", dimension_name="Product", elements=elements, edges=edges)

    def balanced_product_hierarchy(self) -> Hierarchy:
        # Total (3) -> Division (2) -> Family (1) -> SKU (0)
        return self.build_hierarchy(
            {
                ("Total", "Food"): 1,
                ("Total", "Drinks"): 1,
                ("Food", "Snacks"): 1,
                ("Food", "Bakery"): 1,
                ("Drinks", "Soda"): 1,
                ("Snacks", "SKU1"): 1,
                ("Snacks", "SKU2"): 1,
                ("Bakery", "SKU3"): 1,
                ("Soda", "SKU4"): -1,
            }
        )

    def test_rebase_balanced(self):
        hierarchy = self.balanced_product_hierarchy()

        new_leaves = hierarchy.rebase(leaf_level=1)

        self.assertCountEqual(["Snacks", "Bakery", "Soda"], new_leaves)
        for leaf in new_leaves:
            self.assertEqual(Element.Types.NUMERIC, hierarchy.get_element(leaf).element_type)
        for sku in ("SKU1", "SKU2", "SKU3", "SKU4"):
            self.assertNotIn(sku, hierarchy)
        self.assertEqual(
            {("Total", "Food"), ("Total", "Drinks"), ("Food", "Snacks"), ("Food", "Bakery"), ("Drinks", "Soda")},
            set(hierarchy.edges),
        )
        self.assertEqual(Element.Types.CONSOLIDATED, hierarchy.get_element("Food").element_type)

    @staticmethod
    def consolidated_values(hierarchy: Hierarchy, leaf_values: dict) -> dict:
        """value per element (lower case), consolidating leaf_values with the edge weights"""
        values = {}

        def value(name):
            key = name.lower()
            if key not in values:
                children = [(c, w) for (p, c), w in hierarchy.edges.items() if p.lower() == key]
                values[key] = sum(w * value(c) for c, w in children) if children else leaf_values.get(key, 0)
            return values[key]

        for element in hierarchy:
            value(element.name)
        return values

    def test_rebase_reduces_top_level(self):
        # 9 levels: L8 -> L7 -> ... -> L0, with a sibling leaf at each level
        edges = {}
        for level in range(8, 0, -1):
            edges[(f"L{level}", f"L{level - 1}")] = 1
            edges[(f"L{level}", f"Sibling{level - 1}")] = 1
        hierarchy = self.build_hierarchy(edges)

        new_leaves = hierarchy.rebase(leaf_level=3)

        self.assertIn("L3", new_leaves)
        self.assertNotIn("L2", hierarchy)
        # longest path from the top is now 5 edges
        depth, node = 0, "L8"
        while (node, f"L{int(node[1:]) - 1}") in hierarchy.edges:
            depth, node = depth + 1, f"L{int(node[1:]) - 1}"
        self.assertEqual(5, depth)

    def test_rebase_ragged_keeps_short_branch_tops(self):
        hierarchy = self.build_hierarchy(
            {
                ("Total", "Food"): 1,  # Food is level 2
                ("Food", "Snacks"): 1,
                ("Snacks", "SKU1"): 1,
                ("Total", "Misc"): 1,  # Misc is level 1, directly under level 3
                ("Misc", "SKU9"): 1,
                ("Total", "Loose SKU"): 1,  # level 0, directly under level 3
            },
            numeric=["Orphan"],  # level 0 without parent
        )

        new_leaves = hierarchy.rebase(leaf_level=2)

        self.assertCountEqual(["Food", "Misc", "Loose SKU", "Orphan"], new_leaves)
        self.assertEqual(Element.Types.NUMERIC, hierarchy.get_element("Misc").element_type)
        self.assertIn(("Total", "Misc"), hierarchy.edges)
        self.assertNotIn("SKU9", hierarchy)
        self.assertNotIn("Snacks", hierarchy)

    def test_rebase_keeps_alternate_rollup_and_warns(self):
        hierarchy = self.balanced_product_hierarchy()
        hierarchy.add_element("Promo", "Consolidated")
        hierarchy.add_edge("Total", "Promo", 1)
        hierarchy.add_edge("Promo", "SKU1", 1)
        hierarchy.add_edge("Promo", "SKU4", 1)

        with self.assertWarns(UserWarning) as warning:
            new_leaves = hierarchy.rebase(leaf_level=1)

        self.assertIn("Promo", new_leaves)
        self.assertIn(("Total", "Promo"), hierarchy.edges)
        message = str(warning.warning)
        for overlapping in ("Promo", "Snacks", "Soda"):
            self.assertIn(overlapping, message)
        self.assertNotIn("Bakery", message)

    def test_rebase_keeps_leaf_directly_under_surviving_consolidation(self):
        hierarchy = self.balanced_product_hierarchy()
        # SKU1 is also directly under a level 2 consolidation
        hierarchy.add_edge("Food", "SKU1", 1)

        with self.assertWarns(UserWarning):
            new_leaves = hierarchy.rebase(leaf_level=1)

        self.assertIn("SKU1", new_leaves)
        self.assertIn(("Food", "SKU1"), hierarchy.edges)
        self.assertNotIn(("Snacks", "SKU1"), hierarchy.edges)

    def test_rebase_preserves_totals(self):
        hierarchy = self.build_hierarchy(
            {
                ("Total", "Food"): 1,
                ("Total", "Drinks"): 1,
                ("Total", "Misc"): 1,  # short branch
                ("Total", "Promo"): 1,  # alternate rollup
                ("Total", "Loose SKU"): 1,
                ("Food", "Snacks"): 1,
                ("Food", "SKU5"): 2,  # leaf directly under level 2
                ("Drinks", "Soda"): 1,
                ("Snacks", "Chips"): 1,
                ("Snacks", "Nuts"): 1,
                ("Chips", "SKU1"): 1,
                ("Chips", "SKU2"): 0.5,
                ("Nuts", "SKU3"): 1,
                ("Soda", "Cola"): 1,
                ("Cola", "SKU4"): -1,
                ("Misc", "SKU9"): 1,
                ("Promo", "SKU1"): 1,
                ("Promo", "SKU4"): 1,
            }
        )
        leaf_values = {"sku1": 10, "sku2": 20, "sku3": 30, "sku4": 40, "sku5": 50, "sku9": 90, "loose sku": 7}
        original_values = self.consolidated_values(hierarchy, leaf_values)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            new_leaves = hierarchy.rebase(leaf_level=2)

        # load the new leaves with the original (consolidated) values of the same elements
        rebased_values = self.consolidated_values(
            hierarchy, {leaf.lower(): original_values[leaf.lower()] for leaf in new_leaves}
        )
        for element in hierarchy:
            key = element.name.lower()
            self.assertEqual(original_values[key], rebased_values[key], element.name)

    def test_rebase_no_warning_for_clean_cut(self):
        hierarchy = self.balanced_product_hierarchy()

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            hierarchy.rebase(leaf_level=1)

    def test_rebase_level_zero_is_noop(self):
        hierarchy = self.balanced_product_hierarchy()
        edges_before = dict(hierarchy.edges.items())

        new_leaves = hierarchy.rebase(leaf_level=0)

        self.assertCountEqual(["SKU1", "SKU2", "SKU3", "SKU4"], new_leaves)
        self.assertEqual(edges_before, dict(hierarchy.edges.items()))
        self.assertEqual(Element.Types.CONSOLIDATED, hierarchy.get_element("Snacks").element_type)

    def test_rebase_to_top_level(self):
        hierarchy = self.balanced_product_hierarchy()

        new_leaves = hierarchy.rebase(leaf_level=3)

        self.assertEqual(["Total"], new_leaves)
        self.assertEqual(1, len(hierarchy))
        self.assertEqual(0, len(hierarchy.edges))

    def test_rebase_invalid_level(self):
        hierarchy = self.balanced_product_hierarchy()
        for invalid in (-1, 4, 1.5, True, "1"):
            with self.assertRaises(ValueError):
                hierarchy.rebase(leaf_level=invalid)

    def test_rebase_keeps_string_elements(self):
        hierarchy = self.build_hierarchy({("Total", "Food"): 1, ("Food", "SKU1"): 1}, strings=["Comment"])

        hierarchy.rebase(leaf_level=1)

        self.assertIn("Comment", hierarchy)
        self.assertEqual(Element.Types.STRING, hierarchy.get_element("Comment").element_type)

    def test_rebase_case_and_space_insensitive_edges(self):
        hierarchy = self.build_hierarchy(
            {("Total", "Food Items"): 1, ("food items", "SKU 1"): 1, ("Total", "Drinks"): 1}
        )
        hierarchy.add_edge("Drinks", "sku1", 1)

        with self.assertWarns(UserWarning):
            new_leaves = hierarchy.rebase(leaf_level=1)

        self.assertCountEqual(["Food Items", "Drinks"], new_leaves)
        self.assertNotIn("SKU 1", hierarchy)

    def test_rebase_resets_removed_default_member(self):
        hierarchy = self.balanced_product_hierarchy()
        hierarchy._default_member = "SKU1"

        hierarchy.rebase(leaf_level=1)

        self.assertIsNone(hierarchy.default_member)

    def test_rebase_circular_reference(self):
        hierarchy = self.build_hierarchy({("A", "B"): 1, ("B", "A"): 1})
        with self.assertRaises(ValueError):
            hierarchy.rebase(leaf_level=1)


if __name__ == "__main__":
    unittest.main()

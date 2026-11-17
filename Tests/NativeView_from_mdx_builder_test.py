"""NativeView.from_mdx_builder: describing an MdxBuilder as a native view (no server needed)."""

import unittest

from mdxpy import CalculatedMember, MdxBuilder, MdxHierarchySet, MdxTuple, Member

from TM1py.Objects import NativeView


def _subsets(view: NativeView) -> dict:
    return {
        selection.dimension_name: (selection.subset.expression, selection.subset.elements)
        for selection in (*view.columns, *view.rows)
    }


class TestFromMdxBuilder(unittest.TestCase):
    def test_columns_rows_and_titles(self):
        mdx = (
            MdxBuilder.from_cube("Sales")
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all("Year"))
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_leaves("Region"))
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all("Product"))
            .where(Member.of("Version", "Actual"), Member.of("Sales Measure", "Revenue"))
        )

        view = NativeView.from_mdx_builder(mdx, view_name="v")

        self.assertEqual("v", view.name)
        self.assertEqual("sales", view.cube.lower())
        self.assertEqual(["year"], [c.dimension_name for c in view.columns])
        self.assertEqual(["region", "product"], [r.dimension_name for r in view.rows])
        self.assertEqual(MdxHierarchySet.all_leaves("Region").to_mdx(), _subsets(view)["region"][0])
        titles = {t.dimension_name: (t.selected, t.subset.elements) for t in view.titles}
        self.assertEqual({"Version": ("Actual", ["Actual"]), "Sales Measure": ("Revenue", ["Revenue"])}, titles)

    def test_member_list_becomes_static_subset(self):
        members = [Member.of("Region", "North"), Member.of("Region", "O'Brien]s")]
        mdx = MdxBuilder.from_cube("Sales").add_hierarchy_set_to_row_axis(MdxHierarchySet.members(members))

        view = NativeView.from_mdx_builder(mdx)

        expression, elements = _subsets(view)["region"]
        self.assertIsNone(expression)
        self.assertEqual(["North", "O'Brien]s"], elements)

    def test_dimension_names_with_brackets_are_unescaped(self):
        mdx = MdxBuilder.from_cube("Sa]les").add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all("Re]gion"))

        view = NativeView.from_mdx_builder(mdx)

        self.assertEqual("sa]les", view.cube)
        self.assertEqual("re]gion", view.rows[0].dimension_name)

    def test_unsupported_queries_raise_not_implemented(self):
        def base():
            return MdxBuilder.from_cube("Sales").add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all("Region"))

        cases = {
            "tuples on an axis": MdxBuilder.from_cube("Sales").add_member_tuple_to_rows(
                MdxTuple.of(Member.of("Region", "North"), Member.of("Year", "2024"))
            ),
            "calculated member": base().with_member(
                CalculatedMember.avg(
                    "Year", "Year", "Avg", "Sales", MdxHierarchySet.tm1_subset_all("Year"), MdxTuple.of()
                )
            ),
            "third axis": base().add_hierarchy_set_to_axis(2, MdxHierarchySet.tm1_subset_all("Year")),
            "cross join set": MdxBuilder.from_cube("Sales").add_set_to_row_axis(
                MdxHierarchySet.cross_joins(
                    [MdxHierarchySet.tm1_subset_all("Region"), MdxHierarchySet.tm1_subset_all("Year")]
                )
            ),
            "dimension twice on axes": base().add_hierarchy_set_to_column_axis(MdxHierarchySet.all_leaves("Region")),
            "two members of one dimension in WHERE": base().where(
                Member.of("Version", "Actual"), Member.of("Version", "Budget")
            ),
            "WHERE dimension also on an axis": base().where(Member.of("Region", "North")),
            "alternate hierarchy on an axis": MdxBuilder.from_cube("Sales").add_hierarchy_set_to_row_axis(
                MdxHierarchySet.tm1_subset_all("Region", "By Country")
            ),
            "alternate hierarchy in WHERE": base().where(Member.of("Year", "Fiscal", "2024")),
        }
        for case, mdx in cases.items():
            with self.subTest(case):
                with self.assertRaises(NotImplementedError):
                    NativeView.from_mdx_builder(mdx)


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from TM1py import NativeView, ViewAxisSelection, AnonymousSubset, ViewTitleSelection, Subset


class TestNativeView(unittest.TestCase):

    def test_as_mdx_happy_case(self):
        native_view = NativeView(
            cube_name="c1",
            view_name="not_relevant",
            suppress_empty_columns=True,
            suppress_empty_rows=False,
            titles=[ViewTitleSelection("d3", AnonymousSubset("d3", "d3", "", ["e3"]), "e3")],
            columns=[ViewAxisSelection("d1", AnonymousSubset("d1", "d1", "{[d1].[e1]}"))],
            rows=[ViewAxisSelection("d2", AnonymousSubset("d2", "d2", "{[d2].[e2]}"))])

        self.assertEqual(
            "SELECT\r\n"
            "NON EMPTY {[d1].[e1]} DIMENSION PROPERTIES MEMBER_NAME ON 0,\r\n"
            "{[d2].[e2]} DIMENSION PROPERTIES MEMBER_NAME ON 1\r\n"
            "FROM [c1]\r\n"
            "WHERE ([d3].[d3].[e3])",
            native_view.mdx)

    def test_as_mdx_multi_rows_multi_columns(self):
        native_view = NativeView(
            cube_name="c1",
            view_name="not_relevant",
            suppress_empty_columns=True,
            suppress_empty_rows=True,
            titles=[
                ViewTitleSelection("d5", AnonymousSubset("d5", "d5", "", ["e5"]), "e5"),
                ViewTitleSelection("d6", AnonymousSubset("d6", "d6", "", ["e6"]), "e6")],
            columns=[
                ViewAxisSelection("d1", AnonymousSubset("d1", "d1", "{[d1].[e1]}")),
                ViewAxisSelection("d2", AnonymousSubset("d2", "d2", "{[d2].[e2]}"))],
            rows=[
                ViewAxisSelection("d3", AnonymousSubset("d3", "d3", "{[d3].[e3]}")),
                ViewAxisSelection("d4", AnonymousSubset("d4", "d4", "{[d4].[e4]}"))])

        self.assertEqual(
            "SELECT\r\n"
            "NON EMPTY {[d1].[e1]} * {[d2].[e2]} DIMENSION PROPERTIES MEMBER_NAME ON 0,\r\n"
            "NON EMPTY {[d3].[e3]} * {[d4].[e4]} DIMENSION PROPERTIES MEMBER_NAME ON 1\r\n"
            "FROM [c1]\r\n"
            "WHERE ([d5].[d5].[e5],[d6].[d6].[e6])",
            native_view.mdx)

    def test_as_mdx_no_rows(self):
        native_view = NativeView(
            cube_name="c1",
            view_name="not_relevant",
            suppress_empty_columns=True,
            suppress_empty_rows=False,
            titles=[ViewTitleSelection("d3", AnonymousSubset("d3", "d3", "", ["e3"]), "e3")],
            columns=[ViewAxisSelection("d1", AnonymousSubset("d1", "d1", "{[d1].[e1]}"))])

        self.assertEqual(
            "SELECT\r\n"
            "NON EMPTY {[d1].[e1]} DIMENSION PROPERTIES MEMBER_NAME ON 0\r\n"
            "FROM [c1]\r\n"
            "WHERE ([d3].[d3].[e3])",
            native_view.mdx)

    def test_as_mdx_no_columns(self):
        with self.assertRaises(ValueError) as _:
            native_view = NativeView(
                cube_name="c1",
                view_name="not_relevant",
                suppress_empty_columns=True,
                suppress_empty_rows=False,
                titles=[ViewTitleSelection("d3", AnonymousSubset("d3", "d3", "", ["e3"]), "e3")],
                rows=[ViewAxisSelection("d1", AnonymousSubset("d1", "d1", "{[d1].[e1]}"))])

            _ = native_view.mdx

    def test_as_mdx_no_titles(self):
        native_view = NativeView(
            cube_name="c1",
            view_name="not_relevant",
            suppress_empty_columns=True,
            suppress_empty_rows=False,
            columns=[ViewAxisSelection("d1", AnonymousSubset("d1", "d1", "{[d1].[e1]}"))])

        self.assertEqual(
            "SELECT\r\n"
            "NON EMPTY {[d1].[e1]} DIMENSION PROPERTIES MEMBER_NAME ON 0\r\n"
            "FROM [c1]",
            native_view.mdx)

    def test_as_mdx_registered_subsets(self):
        s1 = Subset("s1", "d1", "d1", None, None, ["e1", "e2"])
        s2 = Subset("s2", "d2", "d2", None, None, ["e1", "e2"])
        s3 = Subset("s3", "d3", "d3", None, None, ["e1", "e2"])

        native_view = NativeView(
            cube_name="c1",
            view_name="not_relevant",
            suppress_empty_columns=True,
            suppress_empty_rows=False,
            titles=[ViewTitleSelection("d1", s1, "e1")],
            columns=[ViewAxisSelection("d2", s2)],
            rows=[ViewAxisSelection("d3", s3)])

        self.assertEqual(
            "SELECT\r\n"
            "NON EMPTY {TM1SUBSETTOSET([d2].[d2],\"s2\")} DIMENSION PROPERTIES MEMBER_NAME ON 0,\r\n"
            "{TM1SUBSETTOSET([d3].[d3],\"s3\")} DIMENSION PROPERTIES MEMBER_NAME ON 1\r\n"
            "FROM [c1]\r\n"
            "WHERE ([d1].[d1].[e1])",
            native_view.mdx)

    def test_substitute_title(self):
        s1 = Subset("s1", "d1", "d1", None, None, ["e1", "e2"])
        s2 = Subset("s2", "d2", "d2", None, None, ["e1", "e2"])
        s3 = Subset("s3", "d3", "d3", None, None, ["e1", "e2"])

        native_view = NativeView(
            cube_name="c1",
            view_name="not_relevant",
            suppress_empty_columns=True,
            suppress_empty_rows=False,
            titles=[ViewTitleSelection("d1", s1, "e1")],
            columns=[ViewAxisSelection("d2", s2)],
            rows=[ViewAxisSelection("d3", s3)])

        native_view.substitute_title("d1", "e2")

        self.assertEqual(native_view.titles[0].selected, "e2")

    def test_from_dict_with_unregistered_subsets(self):
        view_json = json.dumps({
            "@odata.type": "ibm.tm1.api.v1.NativeView",
            "Name": "Default",
            "Columns": [{"Subset": {
                "Hierarchy@odata.bind": "Dimensions('d2')/Hierarchies('d2')",
                "Expression": "{[d2].[e3],[d2].[e4]}"}}],
            "Rows": [{"Subset": {
                "Hierarchy@odata.bind": "Dimensions('d1')/Hierarchies('d1')",
                "Elements@odata.bind": [
                    "Dimensions('d1')/Hierarchies('d1')/Elements('e1')",
                    "Dimensions('d1')/Hierarchies('d1')/Elements('e2')"]}}],
            "Titles": [],
            "SuppressEmptyColumns": False,
            "SuppressEmptyRows": False,
            "FormatString": "0.#########"
        })

        view = NativeView.from_json(view_json, cube_name="c1")

        self.assertEqual("Default", view.name)
        self.assertEqual(False, view.suppress_empty_rows)
        self.assertEqual(False, view.suppress_empty_columns)
        self.assertEqual("d2", view.columns[0].dimension_name)
        self.assertEqual("d2", view.columns[0].hierarchy_name)
        self.assertEqual("{[d2].[e3],[d2].[e4]}", view.columns[0].subset.expression)
        self.assertEqual("d1", view.rows[0].dimension_name)
        self.assertEqual("d1", view.rows[0].hierarchy_name)
        self.assertEqual(["e1", "e2"], view.rows[0].subset.elements)

    def test_from_dict_with_ampersand_element_name(self):
        view_json = json.dumps({
            "@odata.type": "ibm.tm1.api.v1.NativeView",
            "Name": "Default",
            "Columns": [{"Subset": {
                "Hierarchy@odata.bind": "Dimensions('d2')/Hierarchies('d2')",
                "Expression": "{[d2].[P&L]}"}}],
            "Rows": [{"Subset": {
                "Hierarchy@odata.bind": "Dimensions('d1')/Hierarchies('d1')",
                "Elements@odata.bind": [
                    "Dimensions('d1')/Hierarchies('d1')/Elements('A&B')"]}}],
            "Titles": [],
            "SuppressEmptyColumns": False,
            "SuppressEmptyRows": False,
            "FormatString": "0.#########"
        })

        view = NativeView.from_json(view_json, cube_name="c1")

        self.assertEqual("Default", view.name)
        self.assertEqual(False, view.suppress_empty_rows)
        self.assertEqual(False, view.suppress_empty_columns)
        self.assertEqual("d2", view.columns[0].subset.dimension_name)
        self.assertEqual("d2", view.columns[0].subset.hierarchy_name)
        self.assertEqual("{[d2].[P&L]}", view.columns[0].subset.expression)
        self.assertEqual("d1", view.rows[0].dimension_name)
        self.assertEqual("d1", view.rows[0].hierarchy_name)
        self.assertEqual(["A&B"], view.rows[0].subset.elements)

    def test_from_dict_with_registered_subsets(self):
        view_json = json.dumps({
            "@odata.type": "ibm.tm1.api.v1.NativeView",
            "Name": "Default", "Columns": [{
                "Subset": {
                    "Hierarchy@odata.bind": "Dimensions('d2')/Hierarchies('d2')",
                    "Expression": "{[d2].[e1],[d2].[e2]}"}}],
            "Rows": [{
                "Subset@odata.bind": "Dimensions('d1')/Hierarchies('d1')/Subsets('Registered Subset')"}],
            "Titles": [],
            "SuppressEmptyColumns": False,
            "SuppressEmptyRows": False,
            "FormatString": "0.#########"})

        view = NativeView.from_json(view_json, cube_name="c1")

        self.assertEqual("Default", view.name)
        self.assertEqual(False, view.suppress_empty_rows)
        self.assertEqual(False, view.suppress_empty_columns)
        self.assertEqual("d1", view.rows[0].dimension_name)
        self.assertEqual("d1", view.rows[0].hierarchy_name)
        self.assertEqual("Registered Subset", view.rows[0].subset.name)
        self.assertEqual("d2", view.columns[0].dimension_name)
        self.assertEqual("d2", view.columns[0].hierarchy_name)
        self.assertEqual("{[d2].[e1],[d2].[e2]}", view.columns[0].subset.expression)

    def test_from_dict_with_registered_subset_in_title(self):
        view_json = json.dumps({
            "@odata.type": "ibm.tm1.api.v1.NativeView",
            "Name": "Default",
            "Columns": [{
                "Subset": {
                    "Hierarchy@odata.bind": "Dimensions('d2')/Hierarchies('d2')",
                    "Expression": "{[d2].[e1],[d2].[e2]}"}}],
            "Rows": [],
            "Titles": [{
                "Subset@odata.bind": "Dimensions('d1')/Hierarchies('d1')/Subsets('Registered Subset')",
                "Selected@odata.bind": "Dimensions('d1')/Hierarchies('d1')/Elements('e1')"}],
            "SuppressEmptyColumns": False,
            "SuppressEmptyRows": False,
            "FormatString": "0.#########"}
        )

        view = NativeView.from_json(view_json, cube_name="c1")

        self.assertEqual("Default", view.name)
        self.assertEqual(False, view.suppress_empty_rows)
        self.assertEqual(False, view.suppress_empty_columns)
        self.assertEqual("d1", view.titles[0].dimension_name)
        self.assertEqual("d1", view.titles[0].hierarchy_name)
        self.assertEqual("Registered Subset", view.titles[0].subset.name)
        self.assertEqual("e1", view.titles[0].selected)
        self.assertEqual("d2", view.columns[0].dimension_name)
        self.assertEqual("d2", view.columns[0].hierarchy_name)
        self.assertEqual("{[d2].[e1],[d2].[e2]}", view.columns[0].subset.expression)
